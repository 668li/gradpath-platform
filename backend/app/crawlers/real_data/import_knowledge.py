import json
from sqlalchemy import text
from app.database import engine

with open('/app/app/crawlers/real_data/knowledge_deep.json') as f:
    data = json.load(f)

print(f'Loaded {len(data)} articles')

with engine.connect() as conn:
    count = 0
    errors = 0
    for item in data:
        try:
            conn.execute(
                text(
                    "INSERT INTO knowledge_articles "
                    "(id, title, content, category, tags, source, metadata, is_published, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :t, :c, :cat, :tags, 'generated', '{}'::jsonb, true, NOW(), NOW()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {'t': item['title'], 'c': item['content'], 'cat': item['category'],
                 'tags': json.dumps(item.get('tags', []))}
            )
            count += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f'Error: {e}')
    conn.commit()
    print(f'Imported {count} knowledge articles ({errors} errors)')
