import sqlite3 as sql
from sqlite3 import Error
from Utilities.utilities import create_connection
import os

if __name__ == "__main__":
    conn = create_connection('Inventory.db')
    cur = conn.cursor()

    with open("schema.sql", 'r') as file:
        sql_script = file.read()

    cur.executescript(sql_script)

    conn.commit()

    print(f"Successfully executed SQL script schema.sql")

    conn.close()
