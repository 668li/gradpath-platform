import sys
sys.path.insert(0, '/app')
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'qas' ORDER BY ordinal_position")).fetchall()
    print('qas columns:', [c[0] for c in cols])
    cols2 = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'experience_posts' ORDER BY ordinal_position")).fetchall()
    print('experience_posts columns:', [c[0] for c in cols2])
    sys_id = conn.execute(text("SELECT id FROM users WHERE email LIKE '%system%'")).scalar()
    if not sys_id:
        sys_id = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
    print(f'system user_id: {sys_id}')
    qas_count = conn.execute(text("SELECT COUNT(*) FROM qas")).scalar()
    print(f'qas count: {qas_count}')
    exp_count = conn.execute(text("SELECT COUNT(*) FROM experience_posts")).scalar()
    print(f'experience_posts count: {exp_count}')
