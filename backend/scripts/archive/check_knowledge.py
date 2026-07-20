from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Check knowledge_articles count and sample
    result = conn.execute(text("SELECT COUNT(*) FROM knowledge_articles"))
    print(f'knowledge_articles current count: {result.scalar()}')
    
    # Check for duplicates again
    result = conn.execute(text("SELECT title, COUNT(*) as cnt FROM knowledge_articles GROUP BY title HAVING COUNT(*) > 1"))
    dups = result.fetchall()
    print(f'\nknowledge_articles with duplicate titles: {len(dups)}')
    if dups:
        print('Sample duplicates:')
        for title, cnt in dups[:5]:
            print(f'  "{title[:60] if title else None}" - count: {cnt}')
    
    # Check if there are posts with same content
    result = conn.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT content, COUNT(*) as cnt 
            FROM knowledge_articles 
            GROUP BY content 
            HAVING COUNT(*) > 1
        ) as subq
    """))
    content_dups = result.scalar()
    print(f'knowledge_articles with duplicate content: {content_dups}')
    
    # Sample some knowledge articles to understand the data
    result = conn.execute(text("""
        SELECT id, title, LENGTH(content) as content_len 
        FROM knowledge_articles 
        ORDER BY created_at DESC 
        LIMIT 5
    """))
    print('\nSample knowledge_articles:')
    for row in result:
        print(f'  id={row[0]}, title={row[1][:60] if row[1] else None}, content_len={row[2]}')
    
    # Check if there were any recent inserts
    result = conn.execute(text("""
        SELECT DATE(created_at) as day, COUNT(*) as cnt 
        FROM knowledge_articles 
        GROUP BY DATE(created_at) 
        ORDER BY day DESC 
        LIMIT 10
    """))
    print('\nknowledge_articles by date:')
    for row in result:
        print(f'  {row[0]}: {row[1]}')
