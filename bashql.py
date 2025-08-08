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
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    # Products with category and inventory
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price INTEGER NOT NULL DEFAULT 0,
            image TEXT DEFAULT '',
            position INTEGER DEFAULT 0,
            category_id INTEGER,
            inventory INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
        """
    )
    # Orders and order items for purchase logging
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            total INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            category_name TEXT DEFAULT '',
            unit_price INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            line_total INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        )
        """
    )
    # Ensure a default category exists
    c.execute("INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'Uncategorized')")
    conn.commit()
    conn.close()

init_boutique_db()


# Create new orders table for signatures


# Create profit table for cleared orders
# c.execute('''
# CREATE TABLE IF NOT EXISTS profit (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     employee_id INTEGER NOT NULL,
#     original_order_id INTEGER NOT NULL,
#     items TEXT NOT NULL,
#     total_paid INTEGER NOT NULL,
#     date_cleared DATE NOT NULL
# )
# ''')

# Migration: Update sites table to add maestro and remove total_owing

# # First, drop the triggers that reference the sites table
# c.execute("DROP TRIGGER IF EXISTS update_site_total_owing")
# c.execute("DROP TRIGGER IF EXISTS update_site_total_owing_after_insert")

# # Create new table structure
# c.execute('''
# CREATE TABLE IF NOT EXISTS sites_new (
#     id TEXT PRIMARY KEY,
#     location TEXT NOT NULL,
#     maestro TEXT DEFAULT 'Boss'
# )
# ''')

# # Copy existing data, setting default maestro value
# c.execute('''
# INSERT INTO sites_new (id, location, maestro)
# SELECT id, location, 'Boss' FROM sites
# ''')

# # Drop old table and rename new one
# c.execute('DROP TABLE sites')
# c.execute('ALTER TABLE sites_new RENAME TO sites')



# # Add 'position' column if it doesn't exist
# try:
#     c.execute("ALTER TABLE products ADD COLUMN position INTEGER")
# except sql.OperationalError:
#     # Column already exists
#     pass

# # Set position = id + 1 for all existing products where position is NULL or 0
# c.execute("UPDATE products SET position = id + 1 WHERE position IS NULL OR position = 0")

# === MIGRATION: Add bosses table and refactor employees to use boss_id ===
# import sqlite3 as sql
# con = sql.connect("Databases/good_food.db")
# c = con.cursor()

# # 1. Create bosses table
# c.execute('''
# CREATE TABLE IF NOT EXISTS bosses (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT NOT NULL,
#     site_id TEXT NOT NULL
# )
# ''')

# # 2. Add boss_id to employees (if not exists)
# try:
#     c.execute("ALTER TABLE employees ADD COLUMN boss_id INTEGER")
# except sql.OperationalError:
#     pass  # Already exists

# # 3. Migrate maestros from sites to bosses, and assign employees
# c.execute("SELECT id, maestro FROM sites")
# sites = c.fetchall()
# site_boss_map = {}  # site_id -> list of boss_ids
# for site_id, maestro_str in sites:
#     maestros = [m.strip() for m in (maestro_str or '').split(';') if m.strip()]
#     boss_ids = []
#     for maestro in maestros:
#         c.execute("INSERT INTO bosses (name, site_id) VALUES (?, ?)", (maestro, site_id))
#         boss_ids.append(c.lastrowid)
#     site_boss_map[site_id] = boss_ids

# # 4. Assign all employees to the first boss of their site
# c.execute("SELECT id, site_id FROM employees")
# employees = c.fetchall()
# for emp_id, site_id in employees:
#     boss_list = site_boss_map.get(site_id)
#     if boss_list:
#         first_boss_id = boss_list[0]
#         c.execute("UPDATE employees SET boss_id = ? WHERE id = ?", (first_boss_id, emp_id))

# # 5. Remove site_id column from employees (SQLite doesn't support DROP COLUMN directly)
# # So we need to recreate the table
# c.execute("PRAGMA table_info(employees)")
# columns = [col[1] for col in c.fetchall()]
# if 'site_id' in columns:
#     c.execute('''
#     CREATE TABLE IF NOT EXISTS employees_new (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         name TEXT,
#         boss_id INTEGER,
#         current_owing INTEGER,
#         items TEXT
#     )
#     ''')
#     c.execute('''
#     INSERT INTO employees_new (id, name, boss_id, current_owing, items)
#     SELECT id, name, boss_id, current_owing, items FROM employees
#     ''')
#     c.execute('DROP TABLE employees')
#     c.execute('ALTER TABLE employees_new RENAME TO employees')

# # 6. Remove maestro column from sites (SQLite doesn't support DROP COLUMN directly)
# c.execute("PRAGMA table_info(sites)")
# site_columns = [col[1] for col in c.fetchall()]
# if 'maestro' in site_columns:
#     c.execute('''
#     CREATE TABLE IF NOT EXISTS sites_new (
#         id TEXT PRIMARY KEY,
#         location TEXT
#     )
#     ''')
#     c.execute('''
#     INSERT INTO sites_new (id, location)
#     SELECT id, location FROM sites
#     ''')
#     c.execute('DROP TABLE sites')
#     c.execute('ALTER TABLE sites_new RENAME TO sites')


con.commit()
con.close()
