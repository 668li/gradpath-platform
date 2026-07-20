import random, uuid
from sqlalchemy import text
from app.database import engine
with engine.connect() as conn:
    qas = conn.execute(text('SELECT id FROM qas ORDER BY RANDOM() LIMIT 40000')).fetchall()
    count = 0
    for (qa_id,) in qas:
        content = random.choice(['建议', '分析', '解答']) + ': detailed answer.' * 2
        conn.execute(
            text("INSERT INTO qa_answers (id, qa_id, content, user_id, is_best, like_count, status, created_at, updated_at) VALUES (:id, :qid, :c, :uid, false, :lc, 'approved', NOW(), NOW())"),
            {'id': str(uuid.uuid4()), 'qid': qa_id, 'c': content, 'uid': '00000000-0000-0000-0000-000000000000', 'lc': random.randint(0, 20)}
        )
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM qa_answers')).scalar()
    print(f'Added {count}, total: {total}')
