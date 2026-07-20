import psycopg2
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='notifications' AND column_name='link'")
if cur.fetchone():
    print("link column already exists")
else:
    cur.execute("ALTER TABLE notifications ADD COLUMN link VARCHAR(500)")
    conn.commit()
    print("link column added")
cur.close()
conn.close()
