from Utilities.utilities import create_connection


if __name__ == "__main__":
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys = ON;")

    with open("schema.sql", 'r') as file:
        sql_script = file.read()

    statements = [s.strip() for s in sql_script.split(';') if s.strip()]
    for stmt in statements:
        cur.execute(stmt + ';')

    conn.commit()

    print(f"Successfully executed SQL script schema.sql")

    conn.close()
