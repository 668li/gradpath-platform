import sys
sys.path.insert(0, '/app')
from sqlalchemy import text
from app.database import engine

conn = engine.connect()
r = conn.execute(text("SELECT metadata->>'major' as major, COUNT(*) as cnt FROM knowledge_articles WHERE source='zhihu' GROUP BY metadata->>'major' ORDER BY cnt DESC"))
total = 0
for row in r:
    print(f"  {row.major}: {row.cnt}")
    total += row.cnt
print(f"Total: {total}")

r2 = conn.execute(text("SELECT category, COUNT(*) as cnt FROM knowledge_articles WHERE source='zhihu' GROUP BY category ORDER BY cnt DESC"))
print("Categories:")
for row in r2:
    print(f"  {row.category}: {row.cnt}")
conn.close()
