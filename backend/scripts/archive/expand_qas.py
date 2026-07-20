import random, uuid
from sqlalchemy import text
from app.database import engine
topics = ['考研择校','专业课复习','公共课备考','调剂策略','复试技巧','考公备考','公务员面试','薪资谈判','简历优化','职业规划','行业选择','创业指导','留学准备','证书考取','技能提升']
statuses = ['open', 'closed', 'draft']
with engine.connect() as conn:
    count = 0
    for _ in range(100000):
        topic = random.choice(topics)
        idx = random.randint(1, 999999)
        title = topic + '-q-' + str(idx)
        content = 'About ' + topic + ', question and discussion.' * 2
        conn.execute(text("INSERT INTO qas (id, user_id, title, content, tags, status, view_count, answer_count, is_resolved, created_at, updated_at) VALUES (gen_random_uuid(), :uid, :t, :c, :tags, :st, :vc, :ac, :ir, NOW(), NOW())"),
            {'uid': '00000000-0000-0000-0000-000000000000', 't': title, 'c': content, 'tags': '[]', 'st': random.choice(statuses), 'vc': random.randint(10, 5000), 'ac': random.randint(0, 10), 'ir': random.choice([True, False])})
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM qas')).scalar()
    print(f'Added {count}, total: {total}')
