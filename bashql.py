import sqlite3 as sql
import re
import os
def smart_capitalize(name):
    name = re.sub(r'[^\w\s/]', ' ', name)
    def cap_word(word, is_first):
        if is_first or len(word) > 3:
            return word.capitalize()
        return word.lower()
    words = re.split(r'(\s+)', name)
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
DB_PATH ="Databases/boutique.db"
con = sql.connect("Databases/boutique.db")
c = con.cursor()
# --- Boutique schema bootstrap ---
def init_boutique_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sql.connect(DB_PATH)
    c = conn.cursor()
    # Categories (formerly sites)
    # c.execute(
    #     """
    #     CREATE TABLE IF NOT EXISTS categories (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL UNIQUE,
    #         position INTEGER DEFAULT 0
    #     )
    #     """
    # )
    # # Products with category and inventory
    # c.execute(
    #     """
    #     CREATE TABLE IF NOT EXISTS products (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL UNIQUE,
    #         price INTEGER NOT NULL DEFAULT 0,
    #         image TEXT DEFAULT '',
    #         position INTEGER DEFAULT 0,
    #         category_id INTEGER,
    #         inventory INTEGER NOT NULL DEFAULT 0,
    #         FOREIGN KEY(category_id) REFERENCES categories(id)
    #     )
    #     """
    # )
    # # Orders and order items for purchase logging
    # c.execute(
    #     """
    #     CREATE TABLE IF NOT EXISTS orders (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         created_at TEXT NOT NULL DEFAULT (datetime('now')),
    #         total INTEGER NOT NULL DEFAULT 0
    #     )
    #     """
    # )
    # c.execute(
    #     """
    #     CREATE TABLE IF NOT EXISTS order_items (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         order_id INTEGER NOT NULL,
    #         product_id INTEGER NOT NULL,
    #         product_name TEXT NOT NULL,
    #         category_name TEXT DEFAULT '',
    #         unit_price INTEGER NOT NULL,
    #         quantity INTEGER NOT NULL,
    #         line_total INTEGER NOT NULL,
    #         FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
    #         FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
    #     )
    #     """
    # )
    # Ensure 'position' column exists on legacy DBs
    try:
        c.execute("ALTER TABLE categories ADD COLUMN position INTEGER DEFAULT 0")
    except sql.OperationalError:
        pass

    # Ensure a default category exists
    # c.execute("INSERT OR IGNORE INTO categories (id, name, position) VALUES (1, 'Otro',1)")

    # Initialize category positions if missing/zero
    c.execute("UPDATE categories SET position = id WHERE position IS NULL OR position = 0")
    conn.commit()
    conn.close()

init_boutique_db()



con.commit()
con.close()
