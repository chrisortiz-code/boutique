import sqlite3 as sql
import os
import random
from datetime import date

DB = "Databases/good_food.db"

co = sql.connect(DB)
c = co.cursor()

# Drop and recreate orders table with date
c.execute("DROP TABLE IF EXISTS orders")
c.execute('''
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    items TEXT NOT NULL,
    signature TEXT,
    date DATE NOT NULL
)
''')

# For each employee, insert a fake order with today's date
c.execute("SELECT id, items FROM employees")
employees = c.fetchall()
today = date.today().isoformat()
for emp_id, items in employees:
    fake_sig = f"static/signatures/sig_{emp_id}.png"
    c.execute("INSERT INTO orders (employee_id, items, signature, date) VALUES (?, ?, ?, ?)", (emp_id, items, fake_sig, today))

co.commit()
co.close()
print(f"Inserted {len(employees)} fake orders.")
