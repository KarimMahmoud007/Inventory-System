import sqlite3
from pathlib import Path
from PySide6.QtSql import QSqlDatabase


def create_connection():
    db_path = str(Path(__file__).resolve().parent.parent / "Database" / "Inventory.db")
    return sqlite3.connect(db_path)


def create_QtConnection():
    db_path = str(Path(__file__).resolve().parent.parent / "Database" / "Inventory.db")

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
