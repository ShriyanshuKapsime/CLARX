import sqlite3
import os

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "price_history.sqlite")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def init_db():
    """Run once to create the database and tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(SCHEMA_PATH, "r") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully!")


if __name__ == "__main__":
    init_db()
