from sqlalchemy import text
from app.database import engine
conn = engine.connect()
cols = conn.execute(text("""
    SELECT column_name, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'grad_school_intel' ORDER BY ordinal_position
""")).fetchall()
for c in cols:
    print(f"{c[0]}  nullable={c[1]}  default={c[2]}")
