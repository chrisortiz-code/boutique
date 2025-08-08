import sqlite3
import re

DB_PATH = "Databases/good_food.db"

def smart_capitalize(name):
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
    return ''.join(result)

def fix_all_names():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name FROM products")
    rows = c.fetchall()
    for prod_id, name in rows:
        new_name = smart_capitalize(name)
        if new_name != name:
            print(f"{name!r} -> {new_name!r}")
            c.execute("UPDATE products SET name = ? WHERE id = ?", (new_name, prod_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_all_names()
    print("✅ Product names formatted.") 