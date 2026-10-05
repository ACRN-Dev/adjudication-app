import sqlite3
import os

db_path = 'backend/acrn_demo.db'
if os.path.exists(db_path):
    print("Found acrn_demo.db, size:", os.path.getsize(db_path))
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Tables:", tables)
    for t in tables:
        count = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"Table {t}: {count} rows")
        if count > 0 and 'participant' in t.lower() or 'batch' in t.lower():
            for row in c.execute(f"SELECT * FROM {t} LIMIT 2"):
                print("  Sample:", row)
else:
    print("No acrn_demo.db")

# Also check postgres if available
try:
    import psycopg2
    conn = psycopg2.connect("postgresql://acrn_user:acrn_dev_password@localhost:5432/acrn_adjudication")
    cur = conn.cursor()
    print("Connected to PostgreSQL!")
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    print("PG Tables:", cur.fetchall())
except Exception as e:
    print("PG connection error:", e)
