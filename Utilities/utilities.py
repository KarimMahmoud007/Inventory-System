import sqlite3 as sql
from sqlite3 import Error
from PySide6.QtSql import QSqlDatabase, QSql, QSqlQuery
from functools import lru_cache


def create_connection():
    conn = None

    try:
        conn = sql.connect(r"C:/Users/karim Mahmoud/PycharmProjects/Inventory/Database/Inventory.db")
        print("Successfully connected to database")
        return conn

    except Error as e:
        print(e)
    return conn

def create_QtConnection():
    db_path = r"C:/Users/karim Mahmoud/PycharmProjects/Inventory/Database/Inventory.db"

    if QSqlDatabase.contains("inventory_connection"):
        return QSqlDatabase.database("inventory_connection")

    db = QSqlDatabase.addDatabase("QSQLITE", "inventory_connection")
    db.setDatabaseName(db_path)

    if not db.open():
        print("Failed to open the database")
        exit()
    else:
        print("Database opened successfully:", db.databaseName())

    return db

@lru_cache
def get_units():
    db = create_QtConnection()
    query = QSqlQuery(db)
    query.exec("SELECT id, name FROM units ORDER BY id")
    units = []
    while query.next():
        units.append((query.value(0), query.value(1)))
    return units

@lru_cache
def get_catalog():
    db = create_QtConnection()
    query = QSqlQuery(db)
    query.exec("SELECT id, name FROM stock")
    catalog = []
    while query.next():
        catalog.append((query.value(0), query.value(1)))
    return catalog

if __name__ == '__main__':
    print ("utilities")