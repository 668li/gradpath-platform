from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    r = conn.execute(text("SELECT COUNT(*) FROM knowledge_articles"))
    total = r.scalar()
    
    r = conn.execute(text(
        "SELECT category, COUNT(*) FROM knowledge_articles "
        "WHERE source = 'generated' GROUP BY category ORDER BY COUNT(*) DESC"
    ))
    print(f"Total knowledge articles: {total}")
    print("New articles by category:")
    for row in r:
        print(f"  {row[0]}: {row[1]}")
