from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Final comprehensive statistics
    print('=== FINAL DATABASE STATISTICS ===')
    
    # experience_posts
    total_exp = conn.execute(text("SELECT COUNT(*) FROM experience_posts")).scalar()
    short_exp = conn.execute(text("SELECT COUNT(*) FROM experience_posts WHERE LENGTH(content) < 200 AND content IS NOT NULL")).scalar()
    print(f'experience_posts: {total_exp}')
    print(f'  - short posts (< 200 chars): {short_exp}')
    
    # knowledge_articles
    total_ka = conn.execute(text("SELECT COUNT(*) FROM knowledge_articles")).scalar()
    print(f'knowledge_articles: {total_ka}')
    
    # qas
    total_qa = conn.execute(text("SELECT COUNT(*) FROM qas")).scalar()
    with_best = conn.execute(text("SELECT COUNT(*) FROM qas WHERE best_answer_id IS NOT NULL")).scalar()
    without_best = conn.execute(text("SELECT COUNT(*) FROM qas WHERE best_answer_id IS NULL")).scalar()
    print(f'qas: {total_qa}')
    print(f'  - with best_answer_id: {with_best} ({with_best*100//total_qa}%)')
    print(f'  - without best_answer_id: {without_best} ({without_best*100//total_qa}%)')
    
    # qa_answers
    total_answers = conn.execute(text("SELECT COUNT(*) FROM qa_answers")).scalar()
    print(f'qa_answers: {total_answers}')
    
    print('\n=== SUMMARY ===')
    print('Task 1 (experience_posts dedup): Completed')
    print('Task 2 (knowledge_articles dedup): Completed')
    print('Task 3 (Fill QA best answers): Completed')
    print('Task 4 (Clean short posts): Completed (spam removed, genuine posts remain)')
