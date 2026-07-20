from sqlalchemy import text
from app.database import engine
conn = engine.connect()
for tbl in ["grad_scoreline_records", "grad_school_intel"]:
    sql = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '" + tbl + "' ORDER BY ordinal_position"
    cols = conn.execute(text(sql)).fetchall()
    print("--- " + tbl + " ---")
    for c in cols:
        print(c[0] + " " + c[1])
