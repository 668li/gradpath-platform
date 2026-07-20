from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # First, let's delete obvious spam posts (phone verification, course ads with price patterns)
    spam_patterns = [
        "应《中华人民共和国网络安全法》",
        "获取短信验证码",
        "火热报名中",
        "¥",
        "共",
        "次课",
        "免费"
    ]
    
    deleted_spam = 0
    for pattern in spam_patterns:
        result = conn.execute(text(f"""
            DELETE FROM experience_posts 
            WHERE content LIKE '%{pattern}%'
            AND LENGTH(content) < 200
        """))
        deleted_spam += result.rowcount
    
    conn.commit()
    print(f'Deleted {deleted_spam} spam posts')
    
    # Now check remaining short posts
    result = conn.execute(text("""
        SELECT COUNT(*) FROM experience_posts
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
    """))
    remaining_short = result.scalar()
    print(f'Remaining short posts: {remaining_short}')
    
    # Sample remaining short posts
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
    
    # Count posts with useful titles but short content
    useful_titles = conn.execute(text("""
        SELECT COUNT(*) FROM experience_posts
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
        AND (title LIKE '%考研%' OR title LIKE '%考公%' OR title LIKE '%复试%' 
             OR title LIKE '%面试%' OR title LIKE '%经验%' OR title LIKE '%上岸%')
    """)).scalar()
    print(f'Posts with useful titles but short content: {useful_titles}')
