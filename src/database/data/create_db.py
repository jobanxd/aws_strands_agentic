import sqlite3
from pathlib import Path

# Base directory (data/)
BASE_DIR = Path(__file__).resolve().parent

# Database path
db_path = BASE_DIR / "kyc_database.db"

# Schema path
schema_path = BASE_DIR / "ddl" / "schema.sql"

# Remove old DB if exists
if db_path.exists():
    db_path.unlink()

# Connect to SQLite DB
conn = sqlite3.connect(db_path)

# Enable foreign keys
conn.execute("PRAGMA foreign_keys = ON;")

cursor = conn.cursor()

# Read schema SQL
with open(schema_path, "r", encoding="utf-8") as schema_file:
    schema_sql = schema_file.read()

try:
    # Execute full schema
    cursor.executescript(schema_sql)

    conn.commit()

    # Verify tables
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name;
    """)

    tables = cursor.fetchall()

    print("Database created successfully!")
    print(f"Database location: {db_path}")

    print("\nTables created:")
    for table in tables:
        print(f"  - {table[0]}")

except sqlite3.Error as e:
    print(f"SQLite error: {e}")

finally:
    conn.close()