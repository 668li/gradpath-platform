from sqlalchemy import text
from app.database import engine
conn = engine.connect()
r = conn.execute(text("""
    SELECT tc.constraint_name, tc.constraint_type, pg_get_constraintdef(c.oid) as def
    FROM information_schema.table_constraints tc
    JOIN pg_constraint c ON c.conname = tc.constraint_name
    WHERE tc.table_name = 'grad_school_intel'
""")).fetchall()
for c in r:
    print(f"{c[0]} ({c[1]}): {c[2]}")
