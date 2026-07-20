from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'milestone_logs' ORDER BY ordinal_position"))
    for row in result:
        print(row)
