import psycopg2
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
# 看test2的收藏
cur.execute("SELECT id FROM users WHERE email='test2@example.com'")
uid = cur.fetchone()[0]
cur.execute("SELECT target_id FROM bookmarks WHERE user_id=%s AND target_type='post'", (uid,))
bids = [r[0] for r in cur.fetchall()]
print(f"test2 bookmarks: {len(bids)}")
for bid in bids:
    cur.execute("SELECT title, tags FROM knowledge_articles WHERE id=%s", (bid,))
    r = cur.fetchone()
    print(f"  {r[0][:40]} | tags: {r[1]}")
# 看时间管理文章有多少
cur.execute("SELECT count(*) FROM knowledge_articles WHERE category='学习方法' AND tags::text LIKE '%时间管理%'")
print("时间管理文章:", cur.fetchone()[0])
cur.execute("SELECT title, tags FROM knowledge_articles WHERE category='学习方法' LIMIT 5")
print("\n样本文章:")
for r in cur.fetchall():
    print(f"  {r[0][:40]} | {r[1]}")
cur.close(); conn.close()
