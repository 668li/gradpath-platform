# -*- coding: utf-8 -*-
"""Import weibo and bilibili data into knowledge_articles table."""
import json
import os
import sys

# Ensure app package is importable
sys.path.insert(0, "/app")

from sqlalchemy import text
from app.database import engine

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def check_schema():
    """Check knowledge_articles table columns."""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'knowledge_articles' ORDER BY ordinal_position"
        ))
        print("knowledge_articles columns:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

def import_data():
    """Import weibo and bilibili data."""
    files = [
        ("weibo_data.json", "weibo"),
        ("bilibili_expand.json", "bilibili_video"),
    ]

    with engine.connect() as conn:
        for fname, cat in files:
            fpath = os.path.join(DATA_DIR, fname)
            if not os.path.exists(fpath):
                print(f"[SKIP] {fpath} not found")
                continue

            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            count = 0
            for item in data:
                try:
                    title = item["title"][:200]
                    content = item.get("content", item.get("description", ""))
                    tags = json.dumps(item.get("tags", []), ensure_ascii=False)
                    metadata = json.dumps({"source": cat, "source_platform": "crawler"}, ensure_ascii=False)

                    conn.execute(text(
                        "INSERT INTO knowledge_articles "
                        "(id, title, content, category, tags, source, metadata, is_published, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :title, :content, :category, :tags, :source, :metadata, true, NOW(), NOW())"
                    ), {
                        "title": title,
                        "content": content,
                        "category": cat,
                        "tags": tags,
                        "source": cat,
                        "metadata": metadata,
                    })
                    count += 1
                except Exception as e:
                    print(f"  Error: {e}")
                    continue

            conn.commit()
            print(f"{cat}: imported {count} records")

if __name__ == "__main__":
    print("=" * 60)
    print("Import Weibo & Bilibili Data")
    print("=" * 60)

    print("\nChecking schema...")
    check_schema()

    print("\nImporting data...")
    import_data()

    print("\nDone!")
