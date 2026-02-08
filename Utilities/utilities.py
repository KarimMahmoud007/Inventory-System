import sqlite3 as sql
from sqlite3 import Error
from PySide6.QtSql  import QSqlDatabase,QSql


def create_connection(db_file):
    conn = None

    try:
        conn = sql.connect(db_file)
        print("Successfully connected to database")
        return conn

    except Error as e:
        print(e)
    return conn

def create_QtConnection():
    db_path = r"C:/Users/karim Mahmoud/PycharmProjects/Inventory/Database/inventory.db"


    if QSqlDatabase.contains("inventory_connection"):
        QSqlDatabase.removeDatabase("inventory_connection")

    db = QSqlDatabase.addDatabase("QSQLITE", "inventory_connection")
    db.setDatabaseName(db_path)

    if not db.open():
        print("Failed to open the database")
        exit()
    else:
        print("Database opened successfully:", db.databaseName())
    return db

if __name__ == '__main__':
    print ("utilities")