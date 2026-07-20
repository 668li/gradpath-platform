# -*- coding: utf-8 -*-
import sys; sys.stdout.reconfigure(encoding='utf-8')
from app.database import engine; from sqlalchemy import text
total = 0
with engine.connect() as conn:
    tables = [('experience_posts','经验帖'),('knowledge_articles','知识文章'),('schools','院校'),('qas','问答'),('qa_answers','回答'),('dark_knowledge','暗知识'),('grad_school_intel','院校情报'),('grad_scoreline_records','分数线'),('companies','公司'),('salary_benchmarks','薪资基准')]
    for t, l in tables:
        r = conn.execute(text(f'SELECT COUNT(*) FROM {t}'))
        c = r.scalar()
        total += c
        print(f'{l:8s}: {c}')
    print(f'\n总计: {total}')
    r = conn.execute(text("SELECT source_platform, COUNT(*) FROM experience_posts GROUP BY source_platform"))
    print('\n经验帖来源:')
    for row in r:
        print(f'  {row[0]}: {row[1]}')
