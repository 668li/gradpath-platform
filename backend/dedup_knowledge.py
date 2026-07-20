from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Deduplicate knowledge_articles by title, keeping longest content
    dups = conn.execute(text("""
        SELECT title, COUNT(*) as cnt 
        FROM knowledge_articles 
        GROUP BY title 
        HAVING COUNT(*) > 1
    """)).fetchall()
    
    deleted = 0
    for title, cnt in dups:
        rows = conn.execute(text("""
            SELECT id, LENGTH(content) as len 
            FROM knowledge_articles 
            WHERE title = :t 
            ORDER BY LENGTH(content) DESC
        """), {'t': title}).fetchall()
        
        # Keep the first (longest), delete the rest
        for row in rows[1:]:
            conn.execute(text("DELETE FROM knowledge_articles WHERE id = :id"), {'id': row[0]})
            deleted += 1
    
    conn.commit()
    
    # Also deduplicate by content (very short content might have different titles)
    content_dups = conn.execute(text("""
        SELECT content, COUNT(*) as cnt 
        FROM knowledge_articles 
        GROUP BY content 
        HAVING COUNT(*) > 1
    """)).fetchall()
    
    content_deleted = 0
    for content, cnt in content_dups:
        rows = conn.execute(text("""
            SELECT id, title 
            FROM knowledge_articles 
            WHERE content = :c 
            ORDER BY created_at DESC
        """), {'c': content}).fetchall()
        
        # Keep the first (most recent), delete the rest
        for row in rows[1:]:
            conn.execute(text("DELETE FROM knowledge_articles WHERE id = :id"), {'id': row[0]})
            content_deleted += 1
    
    conn.commit()
    
    final_count = conn.execute(text("SELECT COUNT(*) FROM knowledge_articles")).scalar()
    print(f'knowledge_articles deduplication:')
    print(f'  Deleted by title: {deleted}')
    print(f'  Deleted by content: {content_deleted}')
    print(f'  Final count: {final_count}')
