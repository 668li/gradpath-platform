from sqlalchemy import text
from app.database import engine
tables = [
    ('dark_knowledge', 'Dark Knowledge'),
    ('grad_scoreline_records', 'Scorelines'),
    ('grad_school_intel', 'School Intel'),
    ('grad_experience_posts', 'Experience Posts'),
    ('users', 'Users'),
]
conn = engine.connect()
print("=" * 60)
print("FULL DATABASE VERIFICATION")
print("=" * 60)
grand_total = 0
for table, label in tables:
    try:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        grand_total += count
        print(f"  {label:25s} ({table}): {count:>10,}")
    except Exception as e:
        print(f"  {label:25s} ({table}): ERROR - {e}")
print("-" * 60)
print(f"  {'GRAND TOTAL':25s}: {grand_total:>10,}")
print("=" * 60)
