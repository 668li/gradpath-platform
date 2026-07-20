from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Analyze short posts by title pattern
    result = conn.execute(text("""
        SELECT title, COUNT(*) as cnt, AVG(LENGTH(content)) as avg_len
        FROM experience_posts
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
        GROUP BY title
        ORDER BY cnt DESC
        LIMIT 20
    """))
    print('Top short post titles:')
    for row in result:
        print(f'  "{row[0][:50] if row[0] else None}" - count: {row[1]}, avg_len: {row[2]:.0f}')
    
    # Count posts that look like spam (phone verification, system messages)
    spam_patterns = ['绑定手机号', '获取短信验证码', '提交', '应《中华人民共和国网络安全法》']
    spam_count = 0
    for pattern in spam_patterns:
        result = conn.execute(text(f"SELECT COUNT(*) FROM experience_posts WHERE content LIKE '%{pattern}%'"))
        count = result.scalar()
        spam_count += count
        print(f'\nPosts containing "{pattern}": {count}')
    
    # Count genuine short posts that could be enriched
    result = conn.execute(text("""
        SELECT COUNT(*) FROM experience_posts
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
        AND content NOT LIKE '%绑定手机号%'
        AND content NOT LIKE '%获取短信验证码%'
        AND content NOT LIKE '%应《中华人民共和国网络安全法》%'
    """))
    genuine_short = result.scalar()
    print(f'\nGenuine short posts (< 200 chars, not spam): {genuine_short}')
    
    # Sample some genuine short posts
    result = conn.execute(text("""
        SELECT id, title, content FROM experience_posts
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
        AND content NOT LIKE '%绑定手机号%'
        AND content NOT LIKE '%获取短信验证码%'
        ORDER BY created_at DESC
        LIMIT 5
    """))
    print('\nSample genuine short posts:')
    for row in result:
        print(f'  id={row[0]}, title={row[1][:40] if row[1] else None}')
        print(f'    content: {row[2][:150] if row[2] else None}')
