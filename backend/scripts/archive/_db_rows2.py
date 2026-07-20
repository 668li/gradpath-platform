import psycopg2
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    try:
        cur.execute(f'SELECT count(*) FROM "{t}"')
        cnt = cur.fetchone()[0]
        if cnt > 0:
            print(f"{t}: {cnt:,}")
    except:
        pass
cur.close()
conn.close()
