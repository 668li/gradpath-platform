from sqlalchemy import text
from app.database import engine
conn = engine.connect()
# Check if there are actually duplicates
r = conn.execute(text("""
    SELECT school_name, major_name, year, count(*)
    FROM grad_school_intel
    GROUP BY school_name, major_name, year
    HAVING count(*) > 1
    LIMIT 5
""")).fetchall()
print(f"Duplicate combos found: {len(r)}")
for c in r:
    print(f"  {c[0]} | {c[1]} | {c[2]} | count={c[3]}")
# Total unique combos
r2 = conn.execute(text("""
    SELECT count(*) FROM (
        SELECT DISTINCT school_name, major_name, year FROM grad_school_intel
    ) t
""")).scalar()
print(f"Unique combos: {r2}")
# Total rows
r3 = conn.execute(text("SELECT count(*) FROM grad_school_intel")).scalar()
print(f"Total rows: {r3}")
