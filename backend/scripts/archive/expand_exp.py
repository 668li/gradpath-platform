import random
import sys
sys.path.insert(0, '/app')
from sqlalchemy import text
from app.database import engine

categories = ['考研上岸','考公上岸','就业经验','调剂经验','复试经验','二战经验','跨考经验','留学经验']

with engine.connect() as conn:
    sys_id = conn.execute(text("SELECT id FROM users WHERE email LIKE '%system%'")).scalar()
    if not sys_id:
        sys_id = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
    print(f'Using user_id: {sys_id}')
    existing = conn.execute(text("SELECT COUNT(*) FROM experience_posts")).scalar()
    print(f'Existing: {existing}, need to add 7500')
    count = 0
    for _ in range(7500):
        cat = random.choice(categories)
        title = cat + '第' + str(random.randint(1,99999)) + '篇经验'
        content = '分享一下我的' + cat + '经历。在整个过程中我深刻体会到了方法论和心态的重要性。' * 3
        conn.execute(text("INSERT INTO experience_posts (id, user_id, title, summary, content, tags, category, view_count, like_count, comment_count, external_view_count, external_like_count, is_pinned, is_anonymous, status, source_platform, source_url, is_verified, created_at, updated_at) VALUES (gen_random_uuid(), :uid, :t, :summary, :c, :tags, :cat, :vc, :lc, :cc, 0, 0, false, false, :status, :sp, '', false, NOW(), NOW())"),
            {'uid': sys_id, 't': title, 'summary': cat + '经验分享摘要', 'c': content, 'tags': '[]', 'cat': cat, 'vc': random.randint(10, 10000), 'lc': random.randint(0, 500), 'cc': random.randint(0, 50), 'status': 'approved', 'sp': 'generated'})
        count += 1
        if count % 1000 == 0:
            print(f'Progress: {count}...')
            conn.commit()
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM experience_posts')).scalar()
    print(f'Added {count} exp, total: {total}')
