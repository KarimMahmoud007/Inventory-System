from pathlib import Path
from Utilities.utilities import create_connection, apply_schema


if __name__ == "__main__":
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys = ON;")
    apply_schema(cur, Path(__file__).parent / "schema.sql")

    conn.commit()

    print(f"Successfully executed SQL script schema.sql")

    conn.close()
