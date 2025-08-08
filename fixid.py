import sqlite3 as sql
import os

DB = "Databases/good_food.db"

co = sql.connect(DB)
c = co.cursor()


# Ensure products table exists
c.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price INT NOT NULL,
    image TEXT
)
''')

# Insert some sample products
sample_products = [
    ("Pizza", 200, "static/images/pizza.png"),
    ("Burger", 150, "static/images/burger.png"),
    ("Salad", 120, "static/images/salad.png")
]
for name, price, image in sample_products:
    c.execute("INSERT INTO products (name, price, image) VALUES (?, ?, ?)", (name, price, image))


co.commit()
co.close()
