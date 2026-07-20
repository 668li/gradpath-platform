from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Delete Fenbi question bank spam posts
    result = conn.execute(text("""
        DELETE FROM experience_posts 
        WHERE title = '粉笔题库'
        AND LENGTH(content) < 200
    """))
    deleted_fenbi = result.rowcount
    conn.commit()
    print(f'Deleted {deleted_fenbi} Fenbi question bank spam posts')
    
    # Delete posts that are just links (content contains "原文链接:" and is short)
    result = conn.execute(text("""
        DELETE FROM experience_posts 
        WHERE content LIKE '%原文链接:%'
        AND LENGTH(content) < 200
    """))
    deleted_links = result.rowcount
    conn.commit()
    print(f'Deleted {deleted_links} link-only posts')
    
    # Check remaining short posts
    result = conn.execute(text("""
        SELECT COUNT(*) FROM experience_posts
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
    """))
    remaining = result.scalar()
    print(f'Remaining short posts: {remaining}')
    
    # Sample remaining to see what's left
    result = conn.execute(text("""
        SELECT id, title, content FROM experience_posts
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 10
    """))
    print('\nSample remaining short posts:')
    for row in result:
        print(f'  id={row[0]}, title={row[1][:50] if row[1] else None}')
        print(f'    content: {row[2][:150] if row[2] else None}')
        print()
    
    # Count posts with genuinely useful titles
    useful_patterns = ['考研', '考公', '复试', '面试', '经验', '上岸', '备考', '复习', '调剂']
    useful_count = 0
    for pattern in useful_patterns:
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM experience_posts
            WHERE LENGTH(content) < 200
            AND title LIKE '%{pattern}%'
        """))
        useful_count += result.scalar()
    
    print(f'Posts with useful exam-related titles: {useful_count}')
    
    # For Task 4, we'll note that enrichment would require AI generation
    # which is beyond scope - we'll just report what we found
    print('\n--- Task 4 Summary ---')
    print('Short posts (< 200 chars) that appear to be genuine experience posts:')
    print(f'  Total remaining after spam cleanup: {remaining}')
    print(f'  With useful exam-related titles: {useful_count}')
    print('Note: Enriching these would require AI-generated content,')
    print('which is beyond the scope of this data cleanup task.')
