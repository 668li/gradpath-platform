import sys
from pathlib import Path
backend_dir = Path("/app")
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='experience_posts' ORDER BY ordinal_position"
    ))
    for row in result:
        print(f"  {row[0]}: {row[1]}")
    
    # Try a manual insert
    row = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
    sys_id = str(row)
    print(f"\nsys_id: {sys_id}")
    
    # Try raw insert
    try:
        conn.execute(text(
            "INSERT INTO experience_posts (id, user_id, title, content, tags, source_platform, status, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :uid, :title, :content, :tags, 'xiaohongshu', 'approved', NOW(), NOW())"
        ), {"uid": sys_id, "title": "test", "content": "test content", "tags": "[]"})
        conn.commit()
        print("Test insert OK")
    except Exception as e:
        print(f"Test insert FAILED: {e}")
