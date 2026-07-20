from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    r = conn.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'knowledge_articles' ORDER BY ordinal_position"
    ))
    for row in r:
        print(f"{row[0]}: {row[1]}")
    
    # Also try a direct insert to see the error
    try:
        conn.execute(text(
            "INSERT INTO knowledge_articles "
            "(id, title, content, category, tags, source, created_at, updated_at) "
            "VALUES (gen_random_uuid(), 'test', 'test', 'test', '[]'::jsonb, 'test', NOW(), NOW())"
        ))
        conn.commit()
        print("\nDirect insert succeeded")
        conn.execute(text("DELETE FROM knowledge_articles WHERE source = 'test'"))
        conn.commit()
    except Exception as e:
        print(f"\nDirect insert error: {e}")
