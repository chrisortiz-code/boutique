import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "Databases/good_food.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Drop payments table to start fresh
c.execute("DROP TABLE IF EXISTS payments")


c.execute('''
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    date DATE NOT NULL DEFAULT (DATE('now')),
    note TEXT
)
''')
def parse_order_total(items_str):
    total = 0
    for item in items_str.split(","):
        item = item.strip()
        if ":" in item and ";" in item:
            try:
                name_price, qty = item.split(";", 1)
                _, price = name_price.split(":", 1)
                price = int(price.strip())
                qty = int(qty.strip())
                total += price * qty
            except Exception:
                continue
    return total

# Get all employees
c.execute("SELECT id FROM employees")
employees = [row[0] for row in c.fetchall()]

# For each employee, get their orders and create payments based on those orders
total_payments = 0
for emp_id in employees:
    c.execute("SELECT id, items, date FROM orders WHERE employee_id = ? ORDER BY date", (emp_id,))
    orders = c.fetchall()
    for order_id, items, order_date in orders:
        order_total = parse_order_total(items)
        if order_total == 0:
            continue
        # Decide how many payments to split this order into (1-3)
        num_payments = random.randint(1, 3)
        remaining = order_total
        pay_date = datetime.strptime(order_date, "%Y-%m-%d")
        for i in range(num_payments):
            if i == num_payments - 1:
                amount = remaining
            else:
                # Randomly split the payment
                amount = random.randint(1, remaining - (num_payments - i - 1))
            remaining -= amount
            pay_date += timedelta(days=random.randint(3, 14))  # 3-14 days after last payment
            note = f"Payment for Order #{order_id} ({i+1}/{num_payments})"
            c.execute(
                "INSERT INTO payments (employee_id, amount, date, note) VALUES (?, ?, ?, ?)",
                (emp_id, amount, pay_date.date().isoformat(), note)
            )
            total_payments += 1

conn.commit()
conn.close()
print(f"Inserted {total_payments} fake payments based on orders.") 