import random, uuid
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    qas = conn.execute(text('SELECT id FROM qas ORDER BY RANDOM() LIMIT 20000')).fetchall()
    count = 0
    for (qa_id,) in qas:
        content = '关于这个问题，' + random.choice(['建议','分析','解答','回复']) + '如下。这是一条来自社区的优质回答，包含详细的分析和建议。' * 2
        conn.execute(text('INSERT INTO qa_answers (id, qa_id, content, user_id, is_best, like_count, status, created_at, updated_at) VALUES (:id, :qid, :c, :uid, :best, :likes, :st, NOW(), NOW())'),
            {'id': str(uuid.uuid4()), 'qid': qa_id, 'c': content, 'uid': '00000000-0000-0000-0000-000000000000', 'best': False, 'likes': 0, 'st': 'approved'})
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM qa_answers')).scalar()
    print(f'Added {count} answers, total: {total}')
