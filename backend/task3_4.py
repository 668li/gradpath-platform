from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Task 3: Fill QA best answers - set best_answer_id to the longest answer for qas without one
    result = conn.execute(text("""
        UPDATE qas 
        SET best_answer_id = subquery.longest_answer_id
        FROM (
            SELECT qa_id AS qid, id AS longest_answer_id
            FROM qa_answers
            WHERE qa_id IN (SELECT id FROM qas WHERE best_answer_id IS NULL)
            AND status = 'approved'
            ORDER BY LENGTH(content) DESC
        ) AS subquery
        WHERE qas.id = subquery.qid
        AND qas.best_answer_id IS NULL
    """))
    updated_qa = result.rowcount
    conn.commit()
    
    remaining = conn.execute(text("SELECT COUNT(*) FROM qas WHERE best_answer_id IS NULL")).scalar()
    print(f'Task 3: Updated {updated_qa} qas with best_answer_id, remaining without: {remaining}')
    
    # Task 4: Enrich short experience posts (content < 200 chars)
    short_posts = conn.execute(text("""
        SELECT id, title, content FROM experience_posts 
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 10
    """)).fetchall()
    
    print(f'\nTask 4: Found {len(short_posts)} sample short posts (< 200 chars)')
    for row in short_posts:
        print(f'  id={row[0]}, title={row[1][:40] if row[1] else None}, content_len={len(row[2]) if row[2] else 0}')
        print(f'    content preview: {row[2][:100] if row[2] else None}')
    
    # Count total short posts
    total_short = conn.execute(text("""
        SELECT COUNT(*) FROM experience_posts 
        WHERE LENGTH(content) < 200
        AND content IS NOT NULL
    """)).scalar()
    print(f'\nTotal short posts (< 200 chars): {total_short}')
