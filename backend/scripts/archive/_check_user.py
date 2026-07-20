import psycopg2
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
# 获取test2用户id
cur.execute("SELECT id FROM users WHERE email='test2@example.com'")
uid = cur.fetchone()
print("test2 user_id:", uid)
if uid:
    uid = uid[0]
    # 收藏
    cur.execute("SELECT count(*) FROM bookmarks WHERE user_id=%s AND target_type='post'", (uid,))
    print("bookmarks:", cur.fetchone()[0])
    # 评估
    cur.execute("SELECT count(*) FROM assessments WHERE user_id=%s", (uid,))
    print("assessments:", cur.fetchone()[0])
    # 经验帖
    cur.execute("SELECT count(*) FROM experience_posts WHERE user_id=%s", (uid,))
    print("experience_posts:", cur.fetchone()[0])
cur.close(); conn.close()
