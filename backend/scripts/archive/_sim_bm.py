import psycopg2, uuid
from datetime import datetime, timedelta
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
cur.execute("SELECT id FROM users WHERE email='test2@example.com'")
uid = cur.fetchone()[0]

# 选2篇时间管理 + 1篇记忆科学
cur.execute("SELECT id FROM knowledge_articles WHERE category='学习方法' AND tags::text LIKE '%时间管理%' LIMIT 2")
tm = [r[0] for r in cur.fetchall()]
cur.execute("SELECT id FROM knowledge_articles WHERE category='学习方法' AND tags::text LIKE '%记忆科学%' LIMIT 1")
mem = [r[0] for r in cur.fetchall()]
selected = (tm + mem)[:3]
print(f"选中: {len(selected)} 篇")

for i, aid in enumerate(selected):
    created = datetime.utcnow() - timedelta(days=i*3)
    bid = str(uuid.uuid4())
    cur.execute("INSERT INTO bookmarks (id, user_id, target_type, target_id, created_at) VALUES (%s, %s, 'post', %s, %s)", 
                (bid, uid, str(aid), created))
    print(f"  inserted bookmark for {aid}")

conn.commit()
print("commit成功")
cur.close(); conn.close()
