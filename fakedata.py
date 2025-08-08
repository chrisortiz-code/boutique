import sqlite3
import random
import string

DB_PATH = "Databases/good_food.db"

SITE_COUNT = 5
EMPLOYEES_PER_SITE = 4

# Helper to generate random strings
def rand_str(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def rand_location():
    cities = ["Santo Domingo", "Santiago", "Punta Cana", "La Romana", "Puerto Plata", "Bavaro", "San Pedro"]
    return random.choice(cities) + " " + rand_str(2)

def rand_items():
    # Simulate the format: name:price;qty, name:price;qty
    products = ["Pizza", "Burger", "Pasta", "Salad", "Juice", "Wrap", "Soup"]
    items = []
    for _ in range(random.randint(1, 4)):
        name = random.choice(products)
        price = random.randint(50, 300)
        qty = random.randint(1, 5)
        items.append(f"{name}:{price};{qty}")
    return ", ".join(items)

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Insert sites
    site_ids = []
    for _ in range(SITE_COUNT):
        site_id = rand_str(8)
        location = rand_location()
        c.execute("INSERT OR IGNORE INTO sites (id, location, total_owing) VALUES (?, ?, 0)", (site_id, location))
        site_ids.append(site_id)

    # Insert employees
    for site_id in site_ids:
        for _ in range(EMPLOYEES_PER_SITE):
            current_owing = random.randint(0, 1000)
            items = rand_items()
            c.execute("INSERT INTO employees (current_owing, items, site_id) VALUES (?, ?, ?)", (current_owing, items, site_id))

    conn.commit()
    conn.close()
    print(f"Inserted {SITE_COUNT} sites and {SITE_COUNT * EMPLOYEES_PER_SITE} employees.")

if __name__ == "__main__":
    main() 