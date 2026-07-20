from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    qa_count = conn.execute(text('SELECT COUNT(*) FROM qa_answers')).scalar()
    avg_len = conn.execute(text('SELECT AVG(LENGTH(content))::int FROM experience_posts')).scalar()
    print(f'qa_answers total: {qa_count}')
    print(f'experience_posts avg length: {avg_len}')
