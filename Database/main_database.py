import sqlite3 as sql
from sqlite3 import Error
import os


def create_connection(db_file):

    conn = None

    try:
        conn = sql.connect(db_file)
        print("Successfully connected to database")
        return conn

    except Error as e:
        print(e)

    return conn


conn = create_connection('Inventory.db')
cur = conn.cursor()

with open("schema.sql", 'r') as file:
    sql_script = file.read()

cur.executescript(sql_script)

conn.commit()

print(f"Successfully executed SQL script schema.sql")

conn.close()
