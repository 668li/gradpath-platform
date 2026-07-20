import psycopg2
conn = psycopg2.connect('postgresql://gradpath:gradpath123@db:5432/gradpath')
cur = conn.cursor()

# List all tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = [row[0] for row in cur.fetchall()]
print("=== All Tables ===")
for t in tables:
    print(t)

# Count each table
print("\n=== Table Counts ===")
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"{t}: {count}")
    except Exception as e:
        print(f"{t}: ERROR - {e}")

conn.close()
