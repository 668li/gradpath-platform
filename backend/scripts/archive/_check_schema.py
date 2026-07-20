import psycopg2
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()
for table in ["knowledge_articles", "civil_service_post_intel", "qas", "grad_adjustment_info", "experience_posts"]:
    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}' ORDER BY ordinal_position")
    cols = cur.fetchall()
    print(f"\n=== {table} ===")
    for c in cols:
        print(f"  {c[0]}: {c[1]}")
cur.close()
conn.close()
