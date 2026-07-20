import psycopg2
conn = psycopg2.connect('postgresql://gradpath:gradpath123@db:5432/gradpath')
cur = conn.cursor()

# Get column info for key tables
tables = ['dark_knowledge', 'grad_school_intel', 'experience_posts', 'qas', 'grad_scoreline_records']
for table in tables:
    cur.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name=%s ORDER BY ordinal_position", (table,))
    cols = cur.fetchall()
    print(f'=== {table} ===')
    for col_name, data_type, nullable in cols:
        print(f'  {col_name}: {data_type} (nullable={nullable})')
    print()

# Show sample rows
print("=== Sample dark_knowledge ===")
cur.execute("SELECT * FROM dark_knowledge LIMIT 1")
cols = [desc[0] for desc in cur.description]
print(f"Columns: {cols}")
row = cur.fetchone()
if row:
    print(f"Sample: {row[:5]}...")

print("\n=== Sample experience_posts ===")
cur.execute("SELECT * FROM experience_posts LIMIT 1")
cols = [desc[0] for desc in cur.description]
print(f"Columns: {cols}")
row = cur.fetchone()
if row:
    print(f"Sample: {row[:5]}...")

print("\n=== Sample qas ===")
cur.execute("SELECT * FROM qas LIMIT 1")
cols = [desc[0] for desc in cur.description]
print(f"Columns: {cols}")
row = cur.fetchone()
if row:
    print(f"Sample: {row[:5]}...")

conn.close()
