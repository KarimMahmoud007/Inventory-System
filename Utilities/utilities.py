import sqlite3
from pathlib import Path
from PySide6.QtSql import QSqlDatabase, QSqlQuery

DB_PATH = Path(__file__).resolve().parent.parent / "Database" / "Inventory.db"
CONNECTION_NAME = "inventory_connection"


def create_connection():
    """Plain sqlite3 connection — used by the schema/seed scripts, which must run
    without PySide6."""
    return sqlite3.connect(str(DB_PATH))


def create_qt_connection():
    if QSqlDatabase.contains(CONNECTION_NAME):
        return QSqlDatabase.database(CONNECTION_NAME)

    db = QSqlDatabase.addDatabase("QSQLITE", CONNECTION_NAME)
    db.setDatabaseName(str(DB_PATH))

    if not db.open():
        raise RuntimeError(f"Failed to open the database at {DB_PATH}: {db.lastError().text()}")

    print("Database opened successfully:", db.databaseName())

    # Per-connection, so it must run at runtime — schema.sql's pragma only covers
    # the sqlite3 setup connection.
    QSqlQuery(db).exec("PRAGMA foreign_keys = ON")

    return db


def close_qt_connection():
    """Close the shared connection. Called from MainWindow.closeEvent.

    Deliberately does not removeDatabase() — models still hold QSqlDatabase
    handles, and removing while those exist is what makes Qt warn.
    """
    if QSqlDatabase.contains(CONNECTION_NAME):
        QSqlDatabase.database(CONNECTION_NAME).close()


def apply_schema(cursor, schema_path):
    """Run schema.sql one statement at a time.

    sqlite3 executescript() would commit and drop the foreign_keys pragma, so the
    statements are split and executed individually. Shared by main_database.py
    and seed.py.
    """
    for statement in [s.strip() for s in Path(schema_path).read_text().split(";") if s.strip()]:
        cursor.execute(statement + ";")
