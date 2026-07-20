from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Delete remaining short posts that are clearly scraped/corrupted content
    # These include posts from 中公教育网, 公务员考试网, etc. with garbled text
    scraped_patterns = [
        '中公教育网',
        '公务员考试网',
        '您现在的位置',
        '首页',
        '地方公务员',
        '备考资料',
        '面试',
        '结构化面试',
        '近期发布',
        '职位表',
        '公告'
    ]
    
    deleted = 0
    for pattern in scraped_patterns:
        result = conn.execute(text(f"""
            DELETE FROM experience_posts 
            WHERE content LIKE '%{pattern}%'
            AND LENGTH(content) < 200
        """))
        deleted += result.rowcount
    
    conn.commit()
    print(f'Deleted {deleted} scraped/corrupted short posts')
    
    # Also delete posts with garbled Chinese (mojibake) - content contains unusual character patterns
    # Posts with very short content that don't look like real experiences
    result = conn.execute(text("""
        DELETE FROM experience_posts 
        WHERE LENGTH(content) < 100
        AND (
            content LIKE '%���%'
            OR title LIKE '%���%'
            OR LENGTH(content) < 30
        )
    """))
    deleted_garbled = result.rowcount
    conn.commit()
    print(f'Deleted {deleted_garbled} garbled/very short posts')
    
    # Final count of remaining short posts
    result = conn.execute(text("""
        SELECT COUNT(*) FROM experience_posts
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
    """))
    remaining_short = result.scalar()
    print(f'\nFinal remaining short posts: {remaining_short}')
    
    # Sample what's left
    result = conn.execute(text("""
        SELECT id, title, content FROM experience_posts
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 5
    """))
    print('\nSample of remaining short posts (should be genuine):')
    for row in result:
        print(f'  id={row[0]}')
        print(f'  title: {row[1][:80] if row[1] else None}')
        print(f'  content: {row[2][:150] if row[2] else None}')
        print()
    
    # Get overall final stats
    total_experience = conn.execute(text("SELECT COUNT(*) FROM experience_posts")).scalar()
    total_knowledge = conn.execute(text("SELECT COUNT(*) FROM knowledge_articles")).scalar()
    total_qas = conn.execute(text("SELECT COUNT(*) FROM qas")).scalar()
    qas_with_best = conn.execute(text("SELECT COUNT(*) FROM qas WHERE best_answer_id IS NOT NULL")).scalar()
    qas_without_best = conn.execute(text("SELECT COUNT(*) FROM qas WHERE best_answer_id IS NULL")).scalar()
    
    print('=== FINAL DATABASE STATISTICS ===')
    print(f'experience_posts: {total_experience}')
    print(f'  - short posts (< 200 chars): {remaining_short}')
    print(f'knowledge_articles: {total_knowledge}')
    print(f'qas: {total_qas}')
    print(f'  - with best_answer_id: {qas_with_best}')
    print(f'  - without best_answer_id: {qas_without_best}')
