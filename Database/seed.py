"""Reset the database and fill it with test data.

    python Database/seed.py

Applies schema.sql (so it works on a missing DB too), wipes every data table, then
inserts stock, batches, recipes and no orders. Plain sqlite3 — no PySide6, so it runs
under any interpreter.

The data is picked to exercise the order flow, not to look realistic:
  - Flour has two batches at different prices → FIFO cost comes out of the older one.
  - Butter has only 0.5 kg → 3 Cakes (0.2 kg each) trips the shortage path.
  - "Mystery Pie" has no ingredient rows → fail-loud "no ingredient mapping".
  - "Odd Brew" asks for Milk in grams (Milk is stored in L) → fail-loud unit error.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "Inventory.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# unit ids seeded by schema.sql: 1 kg, 2 mL, 3 L, 4 g
KG, ML, L, G = 1, 2, 3, 4

STOCK = [
    (1, "Flour", KG),
    (2, "Sugar", KG),
    (3, "Milk", L),
    (4, "Butter", KG),
    (5, "Vanilla", ML),
]

# (id, stock_id, price, production, expiration, quantity, status, added_at)
BATCHES = [
    (1, 1, 3.00, "2026-01-01", "2027-01-01", 2.0, "available", "2026-01-05"),
    (2, 1, 3.50, "2026-02-25", "2027-02-25", 10.0, "available", "2026-03-01"),
    (3, 1, 3.20, "2025-11-01", "2026-11-01", 0.0, "out_of_stock", "2025-11-02"),
    (4, 2, 2.00, "2026-01-20", "2027-01-20", 5.0, "available", "2026-02-01"),
    (5, 3, 1.20, "2026-03-28", "2026-08-28", 1.0, "available", "2026-04-01"),
    (6, 3, 1.40, "2026-04-28", "2026-09-28", 4.0, "available", "2026-05-01"),
    (7, 4, 8.00, "2026-01-15", "2026-12-15", 0.5, "available", "2026-01-20"),
    (8, 5, 0.05, "2026-02-05", "2028-02-05", 250.0, "available", "2026-02-10"),
]

# (id, name, price)
ITEMS = [
    (1, "Bread", 10.00),
    (2, "Cake", 25.00),
    (3, "Milkshake", 12.00),
    (4, "Mystery Pie", 30.00),   # deliberately no ingredients
    (5, "Odd Brew", 8.00),       # deliberately unconvertible unit
]

# (item_id, stock_id, amount, unit)
RECIPE_ROWS = [
    (1, 1, 500, G),
    (1, 2, 50, G),
    (2, 1, 300, G),
    (2, 2, 200, G),
    (2, 4, 0.2, KG),
    (2, 3, 200, ML),
    (2, 5, 5, ML),
    (3, 3, 0.3, L),
    (3, 2, 30, G),
    (5, 3, 100, G),              # g -> L is cross-dimension: fails loudly
]

TABLES_TO_WIPE = [
    "order_batch_consumption", "order_items", "orders",
    "wasted_stock", "items_recipe", "items", "stock_batch", "stock",
    "inspector_state",   # a reset shouldn't leave a daily watch thinking it already ran
]


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    for statement in [s.strip() for s in SCHEMA_PATH.read_text().split(";") if s.strip()]:
        cur.execute(statement + ";")

    for table in TABLES_TO_WIPE:
        cur.execute(f"DELETE FROM {table}")

    cur.executemany("INSERT INTO stock (id, name, unit_of_measure) VALUES (?, ?, ?)", STOCK)
    cur.executemany(
        "INSERT INTO stock_batch "
        "(id, stock_id, price, production_date, expiration_date, quantity, status, added_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", BATCHES)
    cur.executemany("INSERT INTO items (id, name, available, price) VALUES (?, ?, 1, ?)", ITEMS)
    cur.executemany(
        "INSERT INTO items_recipe (item_id, stock_id, amount, unit) VALUES (?, ?, ?, ?)",
        RECIPE_ROWS)

    conn.commit()
    print(f"Seeded {DB_PATH}: {len(STOCK)} stock items, {len(BATCHES)} batches, "
          f"{len(ITEMS)} recipes, 0 orders.")
    conn.close()


if __name__ == "__main__":
    main()
