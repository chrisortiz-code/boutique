from flask import Flask, render_template, session, render_template_string, request, redirect, flash, get_flashed_messages
import sqlite3
from datetime import date, timedelta, datetime
import re
import random
import string
from pathlib import Path
import os
from werkzeug.utils import secure_filename
from flask import url_for
import uuid
import json


app = Flask(__name__)
DB_PATH = "Databases/boutique.db"
UPLOAD_FOLDER = "static/images"


# Add this new function to check for duplicate product names
def check_duplicate_product_name(name, exclude_id=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if exclude_id:
        cursor.execute("SELECT id FROM products WHERE LOWER(name) = ? AND id != ?", (name.lower(), exclude_id))
    else:
        cursor.execute("SELECT id FROM products WHERE LOWER(name) = ?", (name.lower(),))
    result = cursor.fetchone()
    conn.close()
    return result is not None


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html', error=error), 500


if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def get_products(category_id=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if category_id:
        cursor.execute(
            "SELECT id, name, price, image, inventory FROM products WHERE category_id = ? ORDER BY position ASC, id ASC",
            (category_id,),
        )
    else:
        cursor.execute(
            "SELECT id, name, price, image, inventory FROM products ORDER BY position ASC, id ASC"
        )
    products = cursor.fetchall()
    conn.close()
    return products


def get_products_grouped_by_category():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, price, image, inventory, category_id FROM products ORDER BY category_id ASC, position ASC, id ASC"
    )
    rows = cursor.fetchall()
    conn.close()
    products_by_cat = {}
    for pid, name, price, image, inventory, cat_id in rows:
        products_by_cat.setdefault(cat_id, []).append((pid, name, price, image, inventory))
    return products_by_cat


def get_all_products_with_category():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, price, image, inventory, category_id FROM products ORDER BY position ASC, id ASC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def smart_capitalize(name):
    # Remove special characters except spaces and slashes
    name = re.sub(r'[^\w\s/]', ' ', name)
    def cap_word(word, is_first):
        if is_first or len(word) > 3:
            return word.capitalize()
        return word.lower()
    words = re.split(r'(\s+)', name)  # Keep spaces
    result = []
    first = True
    for w in words:
        if w.strip() == '':
            result.append(w)
        else:
            result.append(cap_word(w, first))
            if w.strip():
                first = False
    return ''.join(result).strip()


@app.route("/")
def index():
    cats = get_categories()
    prods = get_all_products_with_category()
    return render_template("index.html", categories=cats, products=prods)

@app.route("/submit_order", methods=["POST"]) 
def submit_order():
    return redirect("/")

def get_categories():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Order by explicit position, then name
    cursor.execute("SELECT id, name FROM categories ORDER BY position ASC, name ASC")
    categories = cursor.fetchall()
    conn.close()
    return categories

@app.route("/inventory")
def inventory_manager():
    # If prior purchase attempt had conflicts, show them as flashes
    if session.get('inventory_conflicts'):
        conflicts = session.pop('inventory_conflicts')
        for conflict in conflicts:
            if conflict.get('reason') == 'not_found':
                flash(f"Producto no encontrado (ID: {conflict.get('product_id')})", "error")
            else:
                flash(
                    f"Conflicto de inventario: {conflict.get('product_name')} (Categoría: {conflict.get('category', 'Desconocida')}) - Solicitado: {conflict.get('requested')}, Disponible: {conflict.get('available')}",
                    "error",
                )
    category_id = request.args.get("category_id")
    try:
        category_id_int = int(category_id) if category_id else None
    except Exception:
        category_id_int = None
    
    if category_id_int:
        # If specific category selected, use get_products for filtered results
        products = get_products(category_id_int)
        # Convert to format with category_id for consistency
        products_with_category = [(p[0], p[1], p[2], p[3], p[4], category_id_int) for p in products]
    else:
        # If no category selected, get all products with category info
        products_with_category = get_all_products_with_category()
    
    categories = get_categories()
    return render_template("inventory.html", products=products_with_category, categories=categories, selected_category=category_id_int)

@app.route("/inventory/update", methods=["POST"])
def inventory_update():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    product_ids = request.form.getlist("product_id")
    received_qtys = request.form.getlist("received_qty")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    updated = 0
    for idx, pid in enumerate(product_ids):
        try:
            qty = int(received_qtys[idx] or 0)
        except Exception:
            qty = 0
        if not pid or qty == 0:
            continue
        c.execute("UPDATE products SET inventory = inventory + ? WHERE id = ?", (qty, pid))
        updated += 1
    conn.commit()
    conn.close()
    if updated:
        flash(f"Inventario actualizado para {updated} producto(s).", "success")
    else:
        flash("No se enviaron cambios de inventario.", "error")
    next_category = request.form.get("category_id") or ""
    return redirect(url_for("inventory_manager", category_id=next_category))

@app.route("/manage", methods=["GET"])
def manage():
    if not session.get("is_admin"):
        return redirect(url_for("admin"))
    categories = get_categories()
    products_by_category = get_products_grouped_by_category()
    return render_template("manage.html", categories=categories, products_by_category=products_by_category)

@app.route("/manage/update_category_positions", methods=["POST"])
def update_category_positions():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    data = request.get_json(silent=True) or {}
    ordered_ids = data.get("ordered_category_ids", [])
    if not isinstance(ordered_ids, list):
        return {"status": "error", "message": "Bad payload"}, 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        for idx, cid in enumerate(ordered_ids, start=1):
            try:
                cid_int = int(cid)
            except Exception:
                continue
            c.execute("UPDATE categories SET position = ? WHERE id = ?", (idx, cid_int))
        conn.commit()
        return {"status": "success"}, 200
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}, 500
    finally:
        conn.close()

@app.route("/manage/add_category", methods=["POST"])
def manage_add_category():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    name = request.form.get("category_name", "").strip()
    if not name:
        flash("Nombre de categoría requerido.", "error")
        return redirect(url_for("manage"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Append to end: set position = current max + 1
        c.execute("SELECT COALESCE(MAX(position), 0) FROM categories")
        next_pos = (c.fetchone()[0] or 0) + 1
        c.execute("INSERT INTO categories (name, position) VALUES (?, ?)", (name, next_pos))
        conn.commit()
        flash(f"Categoría '{name}' agregada.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al agregar categoría: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("manage"))

@app.route("/manage/update_category", methods=["POST"])
def manage_update_category():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    category_id = request.form.get("category_id")
    new_name = request.form.get("new_name", "").strip()
    if not category_id or not new_name:
        flash("Categoría y nombre requeridos.", "error")
        return redirect(url_for("manage"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, category_id))
        conn.commit()
        flash("Categoría actualizada.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al actualizar categoría: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("manage", category_id=category_id))

@app.route("/manage/delete_category", methods=["POST"])
def manage_delete_category():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    category_id = request.form.get("category_id")
    if not category_id:
        flash("Categoría requerida.", "error")
        return redirect(url_for("manage"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Prevent deleting if products exist in this category
        c.execute("SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,))
        if (c.fetchone() or [0])[0] > 0:
            flash("No se puede eliminar categoría con productos. Mueve o elimina los productos primero.", "error")
            conn.close()
            return redirect(url_for("manage", category_id=category_id))
        c.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        flash("Categoría eliminada.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al eliminar categoría: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("manage"))

@app.route("/manage/add_product", methods=["POST"])
def manage_add_product():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    name = smart_capitalize(request.form.get("name", "").strip())
    if check_duplicate_product_name(name):
        flash(f"El nombre del producto '{name}' ya existe.", "error")
        return redirect(url_for("manage"))
    raw_price = request.form.get("price", "0").strip()
    try:
        clean_price = re.sub(r'[^\d-]', '', raw_price)
        price = int(clean_price)
    except Exception:
        price = 0
    category_id = request.form.get("category_id")
    try:
        category_id_int = int(category_id) if category_id else 1
    except Exception:
        category_id_int = 1
    start_inventory = request.form.get("start_inventory", "0").strip()
    try:
        start_inventory_int = int(start_inventory)
    except Exception:
        start_inventory_int = 0
    image = request.files.get("image")
    if image and image.filename:
        filename = secure_filename(image.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path)
    else:
        image_path = ""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT COALESCE(MAX(position), 0) FROM products WHERE category_id = ?", (category_id_int,))
        next_position = (c.fetchone()[0] or 0) + 1
        c.execute(
            "INSERT INTO products (name, price, image, position, category_id, inventory) VALUES (?, ?, ?, ?, ?, ?)",
            (name, price, image_path, next_position, category_id_int, start_inventory_int),
        )
        conn.commit()
        flash(f"Producto '{name}' agregado.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al agregar producto: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("manage", category_id=category_id_int))

@app.route("/manage/update_product", methods=["POST"])
def manage_update_product():
    # 1. Permission Check
    if not session.get("is_admin"):
        return "Unauthorized", 403
    
    # 2. Get Data
    product_id = request.form.get("product_id")
    return_category_id = request.form.get("return_category_id") or ""
    name = smart_capitalize(request.form.get("name", "").strip())
    raw_price = request.form.get("price", "0").strip()
    image = request.files.get("image")
    
    # 3. Validations
    if not product_id:
        flash("Producto faltante.", "error")
        return redirect(url_for("manage", category_id=return_category_id))
    
    if not name:
        flash("El nombre del producto es requerido.", "error")
        return redirect(url_for("manage", category_id=return_category_id))
    
    # Check duplicate (excluding current ID)
    if check_duplicate_product_name(name, exclude_id=int(product_id)):
        flash(f"El nombre del producto '{name}' ya existe.", "error")
        return redirect(url_for("manage", category_id=return_category_id))
    
    # 4. Clean Price
    try:
        clean_price = re.sub(r'[^\d-]', '', raw_price)
        price = int(clean_price)
    except Exception:
        price = 0
    
    # 5. Connect to DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # 6. Handle Image (The Fix)
        if image and image.filename:
            filename = secure_filename(image.filename)
            
            # Use absolute path to be safe on both Windows and Termux
            base_dir = os.path.dirname(os.path.abspath(__file__))
            save_folder = os.path.join(base_dir, 'static', 'images')
            
            # Make sure folder exists
            os.makedirs(save_folder, exist_ok=True)
            
            # A. System Path: For saving the file to the disk (Uses \ on Windows, / on Termux)
            system_path = os.path.join(save_folder, filename)
            image.save(system_path)
            
            # B. Database Path: For the URL (Always uses /)
            # We hardcode this so Android doesn't get confused by Windows backslashes
            db_path = f"static/images/{filename}"
            
            # Update including image
            c.execute("UPDATE products SET name = ?, price = ?, image = ? WHERE id = ?", 
                     (name, price, db_path, product_id))
        else:
            # Update without changing image
            c.execute("UPDATE products SET name = ?, price = ? WHERE id = ?", 
                     (name, price, product_id))
        
        conn.commit()
        flash("Producto actualizado exitosamente.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al actualizar producto: {e}", "error")
    finally:
        conn.close()
    
    return redirect(url_for("manage", category_id=return_category_id))

@app.route("/inventory/add_product", methods=["POST"])
def add_product_inventory():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    name = smart_capitalize(request.form.get("name", "").strip())
    raw_price = request.form.get("price", "0").strip()
    try:
        clean_price = re.sub(r'[^\d-]', '', raw_price)
        price = int(clean_price)
    except Exception:
        price = 0
    category_id = request.form.get("category_id")
    try:
        category_id_int = int(category_id) if category_id else 1
    except Exception:
        category_id_int = 1
    start_inventory = request.form.get("start_inventory", "0").strip()
    try:
        start_inventory_int = int(start_inventory)
    except Exception:
        start_inventory_int = 0
    image = request.files.get("image")
    if image and image.filename:
        filename = secure_filename(image.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path)
    else:
        image_path = ""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Determine next position within category
        c.execute("SELECT COALESCE(MAX(position), 0) FROM products WHERE category_id = ?", (category_id_int,))
        next_position = (c.fetchone()[0] or 0) + 1
        c.execute(
            "INSERT INTO products (name, price, image, position, category_id, inventory) VALUES (?, ?, ?, ?, ?, ?)",
            (name, price, image_path, next_position, category_id_int, start_inventory_int),
        )
        conn.commit()
        flash(f"Producto '{name}' agregado.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al agregar producto: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("inventory_manager", category_id=category_id_int))

@app.route("/api/purchase", methods=["POST"])
def api_purchase():
    # JSON: { items: [{product_id, qty}] }
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])
    if not items:
        return {"error": "No items"}, 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Check inventory
    conflicts = []
    product_cache = {}
    for entry in items:
        try:
            pid = int(entry.get("product_id"))
            qty = int(entry.get("qty"))
        except Exception:
            continue
        c.execute("SELECT inventory, name, price, category_id FROM products WHERE id = ?", (pid,))
        row = c.fetchone()
        if not row:
            conflicts.append({"product_id": pid, "reason": "not_found"})
            continue
        inv, pname, pprice, cat_id = row
        # Get category name
        category_name = "Unknown"
        if cat_id:
            c.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
            cat_row = c.fetchone()
            if cat_row:
                category_name = cat_row[0]
        product_cache[pid] = {"name": pname, "price": int(pprice), "category": category_name}
        if qty > inv:
            conflicts.append({
                "product_id": pid,
                "product_name": pname,
                "requested": qty,
                "available": inv,
                "category": category_name,
            })
    if conflicts:
        conn.close()
        # Store conflicts for display on inventory page and instruct client to redirect
        session['inventory_conflicts'] = conflicts
        return {"status": "conflict", "redirect": "/inventory"}, 409
    # Deduct inventory
    for entry in items:
        pid = int(entry.get("product_id"))
        qty = int(entry.get("qty"))
        c.execute("UPDATE products SET inventory = inventory - ? WHERE id = ?", (qty, pid))
    # Create order + order_items
    # Compute totals with discounts
    order_items_rows = []
    order_total = 0
    for entry in items:
        pid = int(entry.get("product_id"))
        qty = int(entry.get("qty"))
        discount_percent = int(entry.get("discount_percent", 0))
        # Clamp discount between 0 and 25
        discount_percent = max(0, min(25, discount_percent))
        info = product_cache.get(pid) or {"name": "Product #"+str(pid), "price": 0, "category": "Unknown"}
        unit_price = int(info["price"]) if isinstance(info, dict) else 0
        original_line_total = unit_price * qty
        discount_amount = round(original_line_total * discount_percent / 100)
        line_total = original_line_total - discount_amount
        order_total += line_total
        category_name = info.get("category", "Unknown") if isinstance(info, dict) else "Unknown"
        order_items_rows.append((pid, info["name"] if isinstance(info, dict) else str(info), category_name, unit_price, qty, line_total, discount_percent))
    c.execute("INSERT INTO orders (total) VALUES (?)", (order_total,))
    order_id = c.lastrowid
    for pid, pname, category_name, unit_price, qty, line_total, discount_percent in order_items_rows:
        c.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, category_name, unit_price, quantity, line_total, discount_percent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (order_id, pid, pname, category_name, unit_price, qty, line_total, discount_percent)
        )
    conn.commit()
    conn.close()
    return {"status": "ok", "order_id": order_id, "total": order_total}, 200

@app.route("/inventory/bulk_update", methods=["POST"])
def bulk_update_products():
 
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Get all product ids from the form
    ids = request.form.getlist('id')
    names = request.form.getlist('name')
    prices = request.form.getlist('price')
    positions = request.form.getlist('position')
    new_category_ids = request.form.getlist('new_category_id')  # optional per item
    # For file uploads, use request.files.getlist for all images
    images = request.files.getlist('image')

    for idx, prod_id in enumerate(ids):
        name = smart_capitalize(names[idx])
        if check_duplicate_product_name(name, exclude_id=prod_id):
            conn.close()
            flash(f"El nombre del producto '{name}' ya existe. Los nombres de productos deben ser únicos.", "error")
            return redirect("/inventory")
        

    for idx, prod_id in enumerate(ids):
        name = names[idx]
        name = smart_capitalize(name)
        raw_price = prices[idx].strip()
        try:
            clean_price = re.sub(r'[^\d-]', '', raw_price)  # Keep digits and minus sign
            price = int(clean_price)  # Convert to integer, allows negative
        except ValueError:
            price = 0
        position = int(positions[idx]) if positions[idx].isdigit() else idx + 1
        image = images[idx] if idx < len(images) else None
        # Handle image upload or keep existing
        if image and image.filename:
            filename = secure_filename(image.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            image.save(save_path)
            image_path = save_path
        else:
            c.execute("SELECT image FROM products WHERE id = ?", (prod_id,))
            current_image = c.fetchone()
            image_path = current_image[0] if current_image else ''

        # Optional category move
        target_category_id = None
        if idx < len(new_category_ids):
            try:
                val = new_category_ids[idx]
                target_category_id = int(val) if val not in (None, '', 'null') else None
            except Exception:
                target_category_id = None

        if target_category_id is not None:
            # When moving, also set a position at the end of the destination category
            c.execute("SELECT COALESCE(MAX(position), 0) FROM products WHERE category_id = ?", (target_category_id,))
            next_position = (c.fetchone()[0] or 0) + 1
            c.execute(
                "UPDATE products SET name = ?, price = ?, image = ?, position = ?, category_id = ? WHERE id = ?",
                (name, price, image_path, next_position, target_category_id, prod_id)
            )
        else:
            c.execute("UPDATE products SET name = ?, price = ?, image = ?, position = ? WHERE id = ?", (name, price, image_path, position, prod_id))
    conn.commit()
    conn.close()
    return redirect(url_for("manage", category_id=request.form.get('return_category_id') or ''))

@app.route("/products/delete", methods=["POST"])
def delete_product():
    name = request.form["name"]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return redirect(url_for("manage", category_id=request.form.get('return_category_id') or ''))

@app.route("/products/add", methods=["POST"])
def add_product():
    name = request.form["name"]
    name = smart_capitalize(name)

    if check_duplicate_product_name(name):
        flash(f"Product name '{name}' already exists. Product names must be unique.", "error")
        return redirect("/products")
    import re
    raw_price = request.form.get('price', '').strip()
    try:
        clean_price = re.sub(r'[^\d-]', '', raw_price)  # Keep digits and minus sign
        price = int(clean_price)  # Convert to integer, allows negative
    except ValueError:
        price = 0
    image = request.files.get("image")
    if image and image.filename:
        filename = secure_filename(image.filename)
        image_path = os.path.join(UPLOAD_FOLDER,filename)
        image.save(image_path)
    else:
        image_path = ""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Get the current max position
    cursor.execute("SELECT MAX(position) FROM products")
    max_position = cursor.fetchone()[0]
    if max_position is None:
        new_position = 1
    else:
        new_position = max_position + 1
    cursor.execute("INSERT INTO products (name, price, image, position) VALUES (?, ?, ?, ?)", (name, price, image_path, new_position))
    conn.commit()
    conn.close()
    return redirect("/inventory")


app.secret_key = "f92e4b9c638a82e82d1e4e9b4753d1a9fabc1cd2e279c6e7f291f083e82c9b91"


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == "chrisjamesortiz":
            session["is_admin"] = True
            return redirect("/")
        else:
            return render_template("admin.html", error="Wrong password")
    return render_template("admin.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/")


@app.route("/logout", methods=["GET"])
def logout_get():
    print(f"Logout GET called - this should not happen")
    return "Please use the logout button in the footer", 405


def parse_order_total(items):
    return sum(it.get('line_total', 0) for it in items)


@app.route("/chart", methods=["GET"])
def chart():
    # Show all recorded purchases
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, created_at, total FROM orders ORDER BY id DESC")
    orders = c.fetchall()
    # Load items per order
    order_id_to_items = {}
    for oid, _, _ in orders:
        c.execute(
            "SELECT product_name, category_name, unit_price, quantity, line_total, discount_percent FROM order_items WHERE order_id = ? ORDER BY id ASC",
            (oid,)
        )
        order_id_to_items[oid] = c.fetchall()
    conn.close()
    # Transform for template
    entries = []
    for oid, created_at, total in orders:
        order_items = [
            {
                'name': row[0],
                'category': row[1] or 'Unknown',
                'price': row[2],
                'qty': row[3],
                'line_total': row[4],
                'discount_percent': row[5] if len(row) > 5 and row[5] is not None else 0,
            }
            for row in order_id_to_items.get(oid, [])
        ]
        entries.append({
            'id': oid,
            'date': created_at,
            'order_items': order_items,
            'total': total,
        })
    grand_total = sum(e['total'] for e in entries)
    return render_template("chart.html", entries=entries, grand_total=grand_total)


@app.route("/orders/delete", methods=["POST"]) 
def delete_order():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    order_id = request.form.get('order_id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
    c.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return redirect("/chart")


@app.route("/test")
def test():
    return render_template("test.html")


@app.route("/debug")
def debug():
    cats = get_categories()
    prods = get_all_products_with_category()
    return {
        "categories": cats,
        "products": prods,
        "categories_count": len(cats),
        "products_count": len(prods)
    }


@app.route("/gracias")
def gracias():
    receipt_param = request.args.get("receipt", "[]")
    try:
        receipt_data = json.loads(receipt_param)
        # Transform the data to include category as a separate field
        formatted_receipt = []
        for item in receipt_data:
            if len(item) >= 4:  # name, qty, subtotal, category
                formatted_receipt.append({
                    'name': item[0],
                    'qty': item[1], 
                    'subtotal': item[2],
                    'category': item[3]
                })
            else:  # fallback for old format
                formatted_receipt.append({
                    'name': item[0],
                    'qty': item[1],
                    'subtotal': item[2],
                    'category': 'Unknown'
                })
    except:
        formatted_receipt = []
    return render_template("gracias.html", receipt=formatted_receipt)


@app.route("/inventory/update_positions", methods=["POST"])
def update_inventory_positions():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    
    data = request.get_json()
    positions = data.get("positions", [])
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        for item in positions:
            product_id = item.get("id")
            position = item.get("position")
            if product_id and position:
                c.execute("UPDATE products SET position = ? WHERE id = ?", (position, product_id))
        
        conn.commit()
        return {"status": "success"}, 200
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}, 500
    finally:
        conn.close()


@app.route("/manage/update_positions", methods=["POST"])
def update_manage_positions():
    if not session.get("is_admin"):
        return "Unauthorized", 403
    
    data = request.get_json()
    positions = data.get("positions", [])
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        for item in positions:
            product_id = item.get("id")
            position = item.get("position")
            if product_id and position:
                c.execute("UPDATE products SET position = ? WHERE id = ?", (position, product_id))
        
        conn.commit()
        return {"status": "success"}, 200
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}, 500
    finally:
        conn.close()

from flask import render_template_string
import os

@app.route("/debug_upload", methods=["GET", "POST"])
def debug_upload_route():
    # 1. THE HTML (Simple form)
    html_template = """
    <!DOCTYPE html>
    <html>
    <body style="font-family: sans-serif; padding: 20px;">
        <h2>Debug Upload Tool (No Markup)</h2>
        
        <!-- DISPLAY STATUS MESSAGE HERE -->
        {% if msg %}
            <div style="padding:15px; background:#e0ffe0; border:1px solid green; margin-bottom:15px;">
                {{ msg }}
            </div>
        {% endif %}

        {% if err %}
            <div style="padding:15px; background:#ffe0e0; border:1px solid red; margin-bottom:15px;">
                {{ err }}
            </div>
        {% endif %}
        
        <form method="POST" enctype="multipart/form-data" style="background:#ddd; padding:20px;">
            <label>Select Image:</label><br>
            <input type="file" name="image" required>
            <br><br>
            <input type="submit" value="Upload Test">
        </form>
        <br>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """

    msg = ""
    err = ""

    # 2. THE LOGIC
    if request.method == "POST":
        image = request.files.get("image")
        
        if not image or image.filename == "":
            err = "No file selected."
        else:
            try:
                filename = secure_filename(image.filename)
                
                # --- A. FIND PATHS ---
                # Get the folder where app.py lives
                base_dir = os.path.dirname(os.path.abspath(__file__))
                
                # Target: static/images
                save_folder = os.path.join(base_dir, 'static', 'images')
                
                # Create folder if missing
                if not os.path.exists(save_folder):
                    os.makedirs(save_folder)
                    print(f"DEBUG: Created directory {save_folder}")

                # --- B. SAVE TO DISK ---
                # Use system separators (\ on Windows, / on Android)
                system_path = os.path.join(save_folder, filename)
                image.save(system_path)
                
                # --- C. DATABASE URL ---
                # Force forward slashes so it works on web browsers
                db_path = f"static/images/{filename}"
                
                msg = f"SUCCESS! Saved to: {system_path} ||| Database URL would be: {db_path}"
                
            except Exception as e:
                err = f"ERROR: {str(e)}"

    return render_template_string(html_template, msg=msg, err=err)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
