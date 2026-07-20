import psycopg2
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
cur.execute("SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables WHERE n_live_tup > 0 ORDER BY n_live_tup DESC")
for r in cur.fetchall():
    print(f"{r[1]}: {r[2]:,}")
cur.close()
conn.close()
