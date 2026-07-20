from sqlalchemy import text
from app.database import engine
conn = engine.connect()
r1 = conn.execute(text("SELECT count(DISTINCT school_name) FROM grad_school_intel")).scalar()
r2 = conn.execute(text("SELECT count(DISTINCT major_name) FROM grad_school_intel")).scalar()
r3 = conn.execute(text("SELECT count(DISTINCT year) FROM grad_school_intel")).scalar()
print(f"distinct schools={r1} majors={r2} years={r3}")
print(f"max possible combos = {r1 * r2 * r3}")
# Show some schools
schools = conn.execute(text("SELECT DISTINCT school_name FROM grad_school_intel ORDER BY school_name LIMIT 30")).fetchall()
print("Schools sample:", [s[0] for s in schools])
majors = conn.execute(text("SELECT DISTINCT major_name FROM grad_school_intel ORDER BY major_name")).fetchall()
print("Majors:", [m[0] for m in majors])
years = conn.execute(text("SELECT DISTINCT year FROM grad_school_intel ORDER BY year")).fetchall()
print("Years:", [y[0] for y in years])
