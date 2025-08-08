import sqlite3
import random

DB_PATH = "Databases/good_food.db"

first_names = [
    "Chris", "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Jamie", "Riley", "Drew", "Sam",
    "Robin", "Avery", "Skyler", "Cameron", "Quinn", "Jesse", "Harper", "Reese", "Rowan", "Peyton"
]
last_names = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Martinez", "Lopez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson"
]

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
# Ensure 'name' column exists
try:
    c.execute("ALTER TABLE employees ADD COLUMN name TEXT")
except Exception:
    pass  # Ignore if already exists

c.execute("SELECT id FROM employees")
emps = c.fetchall()
for (emp_id,) in emps:
    fname = random.choice(first_names)
    lname = random.choice(last_names)
    full_name = f"{fname} {lname}"
    c.execute("UPDATE employees SET name = ? WHERE id = ?", (full_name, emp_id))
conn.commit()
conn.close()
print(f"Updated {len(emps)} employees with random names.") 