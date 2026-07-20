import psycopg2
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()

# 1. 所有表的数据量
cur.execute("""
SELECT schemaname, relname, n_live_tup 
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC
""")
print("=== 数据库表数据量 ===")
for r in cur.fetchall():
    if r[2] > 0:
        print(f"  {r[1]:40s} {r[2]:>10,}")

# 2. 考公相关数据
print("\n=== 考公数据 ===")
cur.execute("SELECT count(*) FROM civil_service_post_intel")
print(f"  civil_service_post_intel: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM civil_service_dark_knowledge")
print(f"  civil_service_dark_knowledge: {cur.fetchone()[0]}")

# 3. 就业相关数据
print("\n=== 就业数据 ===")
cur.execute("SELECT count(*) FROM market_data")
print(f"  market_data: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM companies")
print(f"  companies: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM salary_benchmarks")
print(f"  salary_benchmarks: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM employment_data")
print(f"  employment_data: {cur.fetchone()[0]}")

# 4. 考研数据
print("\n=== 考研数据 ===")
cur.execute("SELECT count(*) FROM grad_scoreline_records")
print(f"  grad_scoreline_records: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM grad_school_intel")
print(f"  grad_school_intel: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM dark_knowledge")
print(f"  dark_knowledge: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM schools")
print(f"  schools: {cur.fetchone()[0]}")

# 5. 通用数据
print("\n=== 通用数据 ===")
cur.execute("SELECT count(*) FROM knowledge_articles")
print(f"  knowledge_articles: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM experience_posts")
print(f"  experience_posts: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM qas")
print(f"  qas: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM mentors")
print(f"  mentors: {cur.fetchone()[0]}")

cur.close(); conn.close()
