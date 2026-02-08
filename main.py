import sqlite3

db_path = "C:/Users/karim Mahmoud/PycharmProjects/Inventory/Database/inventory.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Tables in SQLite DB:")
for table in tables:
    print(table[0])

conn.close()