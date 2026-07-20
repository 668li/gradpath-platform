import psycopg2
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%post%' OR table_name LIKE '%comment%' ORDER BY table_name")
print("TABLES:", [r[0] for r in cur.fetchall()])
cur.close(); conn.close()
