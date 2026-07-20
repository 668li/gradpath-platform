from sqlalchemy import text
from app.database import engine
conn = engine.connect()
r = conn.execute(text("SELECT count(*), min(year), max(year) FROM grad_school_intel")).fetchone()
print(f"count={r[0]} year_range={r[1]}-{r[2]}")
r2 = conn.execute(text("SELECT count(*) FROM grad_school_intel")).scalar()
print(f"total_rows={r2}")
# Check unique constraint cols
r3 = conn.execute(text("""
    SELECT constraint_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_name = 'grad_school_intel' AND constraint_type = 'UNIQUE'
""")).fetchall()
for c in r3:
    print(f"unique constraint: {c[0]}")
r4 = conn.execute(text("""
    SELECT column_name FROM information_schema.constraint_column_usage
    WHERE table_name = 'grad_school_intel' AND constraint_name = 'uq_school_intel'
""")).fetchall()
for c in r4:
    print(f"  column: {c[0]}")
