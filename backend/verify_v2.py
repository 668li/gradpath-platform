from sqlalchemy import text
from app.database import engine
conn = engine.connect()
# List all tables
tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")).fetchall()
print("All tables:")
for t in tables:
    count = conn.execute(text(f"SELECT COUNT(*) FROM {t[0]}")).scalar()
    print(f"  {t[0]:40s} {count:>10,}")
