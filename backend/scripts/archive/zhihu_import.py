import json
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    sys_id = conn.execute(text("SELECT id FROM users WHERE email = 'system@gradpath.com'")).scalar()
    with open('/app/app/crawlers/real_data/zhihu_playwright.json') as f:
        data = json.load(f)
    # Filter out login wall pages
    valid = [d for d in data if 'zhihu.com' not in d.get('title', '') and len(d.get('content', '')) > 200]
    count = 0
    for item in valid:
        conn.execute(text(
            "INSERT INTO knowledge_articles (id, title, content, category, tags, source, is_published, metadata, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :t, :c, :cat, :tags, :src, true, :meta, NOW(), NOW())"
        ), {
            't': item['title'][:200],
            'c': item['content'][:5000],
            'cat': item.get('category', ''),
            'tags': '[]',
            'src': 'zhihu_playwright',
            'meta': '{}'
        })
        count += 1
    conn.commit()
    total = conn.execute(text('SELECT COUNT(*) FROM knowledge_articles')).scalar()
    print(f'Imported {count} zhihu articles, total ka: {total}')
