import sys
import json
from pathlib import Path

backend_dir = Path("/app")
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.database import engine

with open("/app/app/crawlers/real_data/xiaohongshu_deep.json") as f:
    data = json.load(f)

with engine.connect() as conn:
    sys_id = str(conn.execute(text("SELECT id FROM users LIMIT 1")).scalar())

    count = 0
    for item in data:
        try:
            tags = item.get("tags", [])
            category = tags[0] if tags else "考研"
            conn.execute(
                text(
                    "INSERT INTO experience_posts "
                    "(id, user_id, title, content, tags, category, source_platform, status, "
                    "view_count, like_count, comment_count, external_view_count, external_like_count, "
                    "is_pinned, is_anonymous, is_verified, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :uid, :title, :content, :tags, :category, 'xiaohongshu', 'approved', "
                    "0, 0, 0, 0, 0, false, false, false, NOW(), NOW()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "uid": sys_id,
                    "title": item["title"],
                    "content": item["content"],
                    "tags": json.dumps(tags),
                    "category": category,
                },
            )
            count += 1
        except Exception as e:
            print(f"  skip: {e}")
    conn.commit()
    print(f"Imported {count} xiaohongshu posts")
