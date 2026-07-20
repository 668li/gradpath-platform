from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    rows = conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )).fetchall()
    tables = [r[0] for r in rows]
    
    total = 0
    for t in tables:
        count = conn.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()
        total += count
        print(f'{t}: {count:,}')
    print(f'---')
    print(f'TOTAL: {total:,}')
