from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
tables = [
    ('experience_posts', '经验帖'),
    ('knowledge_articles', '知识文章'),
    ('schools', '院校'),
    ('qas', '问答'),
    ('qa_answers', '回答'),
    ('dark_knowledge', '暗知识'),
    ('grad_school_intel', '院校情报'),
    ('grad_scoreline_records', '分数线'),
    ('companies', '公司'),
    ('salary_benchmarks', '薪资基准'),
]
print('=== FINAL DB COUNTS ===')
for table, label in tables:
    try:
        r = db.execute(text(f'SELECT COUNT(*) FROM {table}'))
        print(f'  {label}: {r.scalar()}')
    except:
        print(f'  {label}: ERROR')
print()
r = db.execute(text("SELECT COUNT(*) FROM experience_posts WHERE source_platform='crawler'"))
print(f'  Crawler experience posts: {r.scalar()}')
r = db.execute(text("SELECT COUNT(*) FROM knowledge_articles WHERE source IS NOT NULL AND source != ''"))
print(f'  Crawler knowledge articles: {r.scalar()}')
db.close()
