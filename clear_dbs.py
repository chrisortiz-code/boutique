# clear_tables.py
import sqlite3

DB_PATH = "Databases/good_food.db"

def clear_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM orders")
    c.execute("DELETE FROM payments")
    c.execute("DELETE FROM profit")
    conn.commit()
    conn.close()
    print("Cleared orders and payments tables.")

if __name__ == "__main__":
    clear_tables()
