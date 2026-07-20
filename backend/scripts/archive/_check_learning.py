import psycopg2
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
cur.execute("SELECT count(*) FROM knowledge_articles WHERE category='学习方法'")
print(f"学习方法文章: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM knowledge_articles WHERE category='考研'")
print(f"考研文章: {cur.fetchone()[0]}")
cur.close(); conn.close()
