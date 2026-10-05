import sqlite3
import os

db_path = r"backend/acrn_demo.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print("Tables in acrn_demo.db:", tables)
    
    # Check canonical_variables distinct in canonical_observations
    if 'canonical_observations' in tables:
        cursor.execute("SELECT DISTINCT canonical_variable FROM canonical_observations ORDER BY canonical_variable")
        vars = [r[0] for r in cursor.fetchall()]
        print("\nDistinct canonical_variables in canonical_observations:")
        print(vars)

    # Check raw observations or staging or source uploads
    for tbl in tables:
        if any(w in tbl.lower() for w in ['raw', 'upload', 'source', 'stage', 'file', 'batch', 'observation', 'patient', 'participant']):
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            cnt = cursor.fetchone()[0]
            print(f"Table {tbl}: {cnt} rows")

    # Let's inspect source_batches or raw_records
    for tbl in tables:
        cursor.execute(f"PRAGMA table_info({tbl})")
        cols = [c[1] for c in cursor.fetchall()]
        print(f"Table {tbl} columns:", cols)
