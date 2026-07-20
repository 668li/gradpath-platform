import psycopg2, json
conn = psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur = conn.cursor()

# 考公数据
print("=== 考公 civil_service_post_intel ===")
cur.execute("SELECT count(*) FROM civil_service_post_intel")
print(f"  总数: {cur.fetchone()[0]}")
cur.execute("SELECT id, region, department, post_name, real_competition FROM civil_service_post_intel LIMIT 3")
for r in cur.fetchall():
    print(f"  {r}")

print("\n=== 考公 civil_service_dark_knowledge ===")
cur.execute("SELECT count(*) FROM civil_service_dark_knowledge")
print(f"  总数: {cur.fetchone()[0]}")
cur.execute("SELECT id, stage, title, importance FROM civil_service_dark_knowledge LIMIT 3")
for r in cur.fetchall():
    print(f"  {r}")

# 就业数据
print("\n=== 就业 companies ===")
cur.execute("SELECT count(*) FROM companies")
print(f"  总数: {cur.fetchone()[0]}")
cur.execute("SELECT id, name, industry, size FROM companies LIMIT 3")
for r in cur.fetchall():
    print(f"  {r}")

print("\n=== 就业 salary_benchmarks ===")
cur.execute("SELECT count(*) FROM salary_benchmarks")
print(f"  总数: {cur.fetchone()[0]}")
cur.execute("SELECT id, company, position, city, salary_min, salary_max FROM salary_benchmarks LIMIT 3")
for r in cur.fetchall():
    print(f"  {r}")

print("\n=== 就业 market_data ===")
cur.execute("SELECT count(*) FROM market_data")
print(f"  总数: {cur.fetchone()[0]}")
cur.execute("SELECT id, indicator, category, value, region FROM market_data LIMIT 3")
for r in cur.fetchall():
    print(f"  {r}")

print("\n=== 就业 career_company_intel ===")
cur.execute("SELECT count(*) FROM career_company_intel")
print(f"  总数: {cur.fetchone()[0]}")

print("\n=== 就业 career_dark_knowledge ===")
cur.execute("SELECT count(*) FROM career_dark_knowledge")
print(f"  总数: {cur.fetchone()[0]}")

# 考研暗知识
print("\n=== 考研 dark_knowledge ===")
cur.execute("SELECT count(*) FROM dark_knowledge")
print(f"  总数: {cur.fetchone()[0]}")
cur.execute("SELECT id, stage, title, importance FROM dark_knowledge LIMIT 3")
for r in cur.fetchall():
    print(f"  {r}")

print("\n=== 考研 grad_school_intel ===")
cur.execute("SELECT count(*) FROM grad_school_intel")
print(f"  总数: {cur.fetchone()[0]}")

print("\n=== 考研 grad_scoreline_records ===")
cur.execute("SELECT count(*) FROM grad_scoreline_records")
print(f"  总数: {cur.fetchone()[0]}")

cur.close(); conn.close()
