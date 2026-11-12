
import sqlite3
from contextlib import contextmanager
from pathlib import Path


# Find the solution directory.
BASE_DIR = Path(__file__).resolve().parents[1]

# Location of our SQL schema.
SCHEMA_PATH = BASE_DIR / "schema.sql"

# Location of our actual SQLite database.
DATABASE_PATH = BASE_DIR / "interaction_ledger.db"


@contextmanager
def get_connection():
    """
    Open a database connection and manage its lifecycle.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    # Return database rows in a dictionary-like format.
    connection.row_factory = sqlite3.Row

    # Enable foreign key enforcement.
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def initialize_database():
    """
    Create all database tables and indexes.
    """

    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection() as connection:
        connection.executescript(schema)

    print(f"Database initialized at: {DATABASE_PATH}")
