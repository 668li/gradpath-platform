import psycopg2, json, uuid
from datetime import datetime, timedelta
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
cur.execute("SELECT id FROM users WHERE email='test2@example.com'")
uid = cur.fetchone()[0]

# 模拟用户收藏3篇学习方法文章（时间衰减测试）
cur.execute("SELECT id, tags FROM knowledge_articles WHERE category='学习方法' AND tags::text LIKE '%时间管理%' LIMIT 2")
tm_articles = cur.fetchall()
cur.execute("SELECT id, tags FROM knowledge_articles WHERE category='学习方法' AND tags::text LIKE '%记忆科学%' LIMIT 1")
mem_articles = cur.fetchall()

all_selected = (tm_articles + mem_articles)[:3]
for i, (aid, tags) in enumerate(all_selected):
    created = datetime.utcnow() - timedelta(days=i*5)
    bid = str(uuid.uuid4())
    cur.execute("INSERT INTO bookmarks (id, user_id, target_type, target_id, created_at) VALUES (%s, %s, 'post', %s, %s)", 
                (bid, uid, str(aid), created))

# 模拟评估数据
cur.execute("INSERT INTO assessments (id, user_id, result_code, recommended_directions, created_at) VALUES (%s, %s, 'RIA', %s, NOW())",
            (str(uuid.uuid4()), uid, json.dumps(["开发","数据"])))

conn.commit()
print(f"插入了 {len(all_selected)} 条收藏 + 1 条评估")
cur.close(); conn.close()
