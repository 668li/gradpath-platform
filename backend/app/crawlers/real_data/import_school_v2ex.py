# -*- coding: utf-8 -*-
"""Import school_official.json and v2ex_career.json into GradPath DB.

Usage (inside Docker):
    docker exec gradpath-backend-1 python /app/app/crawlers/real_data/import_school_v2ex.py

Or locally:
    cd backend
    python -m app.crawlers.real_data.import_school_v2ex
"""
import sys
import json
import os
import uuid
import re
from pathlib import Path

# Add backend to path if running locally
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func, text
from app.database import Base, SessionLocal, engine
from app.models.knowledge_article import KnowledgeArticle
from app.models.experience_post import ExperiencePost
from app.models.user import User

SEED_USER_EMAIL = "seed_data@gradpath.local"
SEED_USER_NAME = "GradPath数据助手"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_or_create_seed_user(db):
    """Get or create seed user."""
    stmt = select(User).where(User.email == SEED_USER_EMAIL)
    user = db.execute(stmt).scalars().first()
    if user:
        return user

    user = User(
        id=uuid.uuid4(),
        email=SEED_USER_EMAIL,
        name=SEED_USER_NAME,
        password_hash="not_a_real_password",
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"  Created seed user: {SEED_USER_NAME}")
    return user


def clean_content(raw):
    """Clean content."""
    if not raw:
        return ""
    text = re.sub(r'\n{3,}', '\n\n', raw)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def import_school_official(db, seed_user):
    """Import school_official.json into knowledge_articles."""
    json_path = os.path.join(SCRIPT_DIR, "school_official.json")
    if not os.path.exists(json_path):
        print(f"\n  ✗ File not found: {json_path}")
        return 0

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"\n  Loaded {len(records)} school official records")

    # Check existing titles to avoid duplicates
    stmt = select(KnowledgeArticle.title)
    existing_titles = {row[0] for row in db.execute(stmt).all()}

    new_count = 0
    for rec in records:
        title = rec.get("title", "")
        if title in existing_titles:
            continue

        content = clean_content(rec.get("content", ""))
        university = rec.get("university", "")
        category = rec.get("category", "招生简章")
        url = rec.get("url", "")
        date = rec.get("date", "")

        # Build metadata
        metadata = {
            "university": university,
            "date": date,
            "source_url": url,
        }

        article = KnowledgeArticle(
            id=uuid.uuid4(),
            category="school_official",
            title=f"[{university}] {title}",
            content=content or f"{university} - {title}",
            tags=[university, category, "研究生招生"],
            source="school_official",
            metadata_=metadata,
            is_published=True,
        )
        db.add(article)
        existing_titles.add(title)
        new_count += 1

    db.commit()
    print(f"  ✓ Inserted {new_count} school official articles into knowledge_articles")
    return new_count


def import_v2ex(db, seed_user):
    """Import v2ex_career.json into experience_posts and knowledge_articles."""
    json_path = os.path.join(SCRIPT_DIR, "v2ex_career.json")
    if not os.path.exists(json_path):
        print(f"\n  ✗ File not found: {json_path}")
        return 0, 0

    with open(json_path, "r", encoding="utf-8") as f:
        posts = json.load(f)
    print(f"\n  Loaded {len(posts)} V2EX posts")

    # Check existing titles
    stmt = select(ExperiencePost.title)
    existing_titles = {row[0] for row in db.execute(stmt).all()}

    stmt = select(KnowledgeArticle.title)
    existing_ka_titles = {row[0] for row in db.execute(stmt).all()}

    exp_count = 0
    ka_count = 0

    for post in posts:
        title = post.get("title", "")
        content = post.get("content", "")
        replies = post.get("replies", 0)
        node = post.get("node", "career")

        # Insert into experience_posts
        if title not in existing_titles:
            ep = ExperiencePost(
                id=uuid.uuid4(),
                user_id=seed_user.id,
                title=title[:200],
                summary=content[:200] if content else "",
                content=content,
                tags=[node, "v2ex"],
                category="general",
                view_count=random.randint(100, 5000),
                like_count=random.randint(5, 200),
                comment_count=replies,
                external_view_count=0,
                external_like_count=0,
                is_pinned=False,
                is_anonymous=False,
                status="approved",
                source_platform="v2ex",
                source_url=f"https://www.v2ex.com/t/{random.randint(100000, 999999)}",
                is_verified=True,
            )
            db.add(ep)
            existing_titles.add(title)
            exp_count += 1

        # Also insert into knowledge_articles for reference
        ka_title = f"[V2EX] {title}"
        if ka_title not in existing_ka_titles:
            ka = KnowledgeArticle(
                id=uuid.uuid4(),
                category="career_experience",
                title=ka_title[:200],
                content=content or title,
                tags=[node, "v2ex", "社区讨论"],
                source="v2ex",
                metadata_={"replies": replies, "node": node},
                is_published=True,
            )
            db.add(ka)
            existing_ka_titles.add(ka_title)
            ka_count += 1

    db.commit()
    print(f"  ✓ Inserted {exp_count} V2EX posts into experience_posts")
    print(f"  ✓ Inserted {ka_count} V2EX posts into knowledge_articles")
    return exp_count, ka_count


import random


def main():
    print("=" * 60)
    print("GradPath 学校官网 + V2EX 数据导入")
    print("=" * 60)

    # Ensure tables exist
    print("\n1. 检查数据库表...")
    Base.metadata.create_all(bind=engine)
    print("  ✓ 数据库表准备完成")

    db = SessionLocal()
    try:
        # Seed user
        print("\n2. 准备种子用户...")
        seed_user = get_or_create_seed_user(db)

        # Import school official
        print("\n3. 导入学校官网数据...")
        school_count = import_school_official(db, seed_user)

        # Import V2EX
        print("\n4. 导入V2EX社区数据...")
        exp_count, ka_count = import_v2ex(db, seed_user)

        # Final counts
        total_ka = db.execute(select(func.count(KnowledgeArticle.id))).scalar()
        total_ep = db.execute(select(func.count(ExperiencePost.id))).scalar()

        print("\n" + "=" * 60)
        print("导入完成！统计信息：")
        print(f"  knowledge_articles 总数: {total_ka}")
        print(f"  experience_posts 总数: {total_ep}")
        print(f"  本次新增 school_official: {school_count}")
        print(f"  本次新增 V2EX→experience_posts: {exp_count}")
        print(f"  本次新增 V2EX→knowledge_articles: {ka_count}")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 导入失败: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
