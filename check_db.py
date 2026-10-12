import sqlite3

conn = sqlite3.connect('securevision.db')
cursor = conn.cursor()

# Get all tables
tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)

# Check if alembic_version exists
has_alembic = 'alembic_version' in tables
print(f"\nalembic_version exists: {has_alembic}")

if has_alembic:
    version = cursor.execute("SELECT version_num FROM alembic_version").fetchone()
    print(f"Current migration version: {version[0] if version else 'None'}")

# Check scan_history schema
if 'scan_history' in tables:
    columns = cursor.execute("PRAGMA table_info(scan_history)").fetchall()
    print(f"\nscan_history columns: {[col[1] for col in columns]}")

conn.close()
