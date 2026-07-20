# -*- coding: utf-8 -*-
"""Import Firecrawl-scraped articles into GradPath database.

Reads firecrawl_scraped.json and inserts as ExperiencePost + KnowledgeArticle.

Usage (inside Docker):
    docker exec gradpath-backend-1 python /app/app/crawlers/real_data/firecrawl_import.py

Or locally:
    cd backend
    python -m app.crawlers.real_data.firecrawl_import
"""
import sys
import json
import os
import re
import uuid
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from app.database import Base, SessionLocal, engine
from app.models.user import User
from app.models.experience_post import ExperiencePost
from app.models.knowledge_article import KnowledgeArticle

SEED_USER_EMAIL = "firecrawl_seed@gradpath.local"
SEED_USER_NAME = "考研数据采集"

CATEGORY_MAP = {
    "初试": "初试",
    "复试": "复试",
    "调剂": "调剂",
    "择校": "择校",
    "备考": "复习",
    "政策": "general",
    "分数线": "初试",
    "专业分析": "general",
    "经验分享": "general",
    "专业": "general",
    "院校": "择校",
    "复习": "复习",
}


def clean_content(raw):
    if not raw:
        return ""
    text = re.sub(r'\{[^}]*\}', '', raw)
    text = re.sub(r'/\*!.*?\*/', '', text)
    text = re.sub(r'--tw-[^:]+:[^;]+;', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def get_or_create_seed_user(db):
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
    print(f"  Created seed user: {SEED_USER_NAME} ({user.id})")
    return user


def get_existing_urls(db):
    stmt = select(ExperiencePost.source_url).where(
        ExperiencePost.source_url.isnot(None)
    )
    return {row[0] for row in db.execute(stmt).all()}


def get_existing_ka_urls(db):
    stmt = select(KnowledgeArticle.source).where(
        KnowledgeArticle.source.isnot(None)
    )
    return {row[0] for row in db.execute(stmt).all()}


def import_articles(db, articles, existing_urls, seed_user):
    new_count = 0
    skip_count = 0

    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "未命名文章")

        if url in existing_urls:
            skip_count += 1
            continue

        raw_content = article.get("content", "")
        content = clean_content(raw_content)

        if len(content) < 50:
            content = f"{title}\n\n{content}\n\n原文链接: {url}"

        category_raw = article.get("category", "经验分享")
        category = CATEGORY_MAP.get(category_raw, "general")

        summary = content[:200].replace("\n", " ").strip()
        if len(summary) > 197:
            summary = summary[:197] + "..."

        post = ExperiencePost(
            id=uuid.uuid4(),
            user_id=seed_user.id,
            title=title[:200],
            summary=summary,
            content=content,
            tags=[category_raw, "kaoyan.com", "firecrawl"],
            category=category,
            view_count=0,
            like_count=0,
            comment_count=0,
            external_view_count=0,
            external_like_count=0,
            is_pinned=False,
            is_anonymous=False,
            status="approved",
            source_platform="crawler",
            source_url=url,
            is_verified=True,
        )
        db.add(post)
        existing_urls.add(url)
        new_count += 1

    db.commit()
    return new_count, skip_count


def import_knowledge_articles(db, articles, existing_ka_urls):
    new_count = 0

    # Select articles suitable for knowledge base
    knowledge_suitable = [
        a for a in articles
        if a.get("category") in ("政策", "分数线", "专业分析")
        and a.get("url", "") not in existing_ka_urls
    ]

    for article in knowledge_suitable[:30]:
        url = article.get("url", "")
        title = article.get("title", "")
        content = clean_content(article.get("content", ""))

        if len(content) < 100:
            continue

        ka = KnowledgeArticle(
            id=uuid.uuid4(),
            category="education_path",
            title=title[:200],
            content=content[:10000],
            tags=[article.get("category", ""), "考研", "firecrawl"],
            source=url,
            metadata_={
                "source_site": article.get("source", ""),
                "scraped_at": article.get("scraped_at", ""),
            },
            is_published=True,
        )
        db.add(ka)
        existing_ka_urls.add(url)
        new_count += 1

    db.commit()
    return new_count


def main():
    print("=" * 60)
    print("GradPath Firecrawl 数据导入脚本")
    print("=" * 60)

    print("\n1. 检查数据库表...")
    Base.metadata.create_all(bind=engine)
    print("  OK 数据库表准备完成")

    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firecrawl_scraped.json")
    if not os.path.exists(json_path):
        print(f"\nERROR: 文件不存在: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    print(f"\n2. 加载数据: {len(articles)} 篇文章")

    db = SessionLocal()
    try:
        print("\n3. 准备种子用户...")
        seed_user = get_or_create_seed_user(db)

        existing_urls = get_existing_urls(db)
        print(f"  数据库中已有 {len(existing_urls)} 篇经验帖")

        print("\n4. 导入经验帖...")
        new_count, skip_count = import_articles(db, articles, existing_urls, seed_user)
        print(f"  OK 新增 {new_count} 篇经验帖")
        print(f"  - 跳过 {skip_count} 篇（已存在）")

        print("\n5. 导入知识库文章...")
        existing_ka_urls = get_existing_ka_urls(db)
        ka_count = import_knowledge_articles(db, articles, existing_ka_urls)
        print(f"  OK 新增 {ka_count} 篇知识库文章")

        total_posts = db.execute(select(func.count(ExperiencePost.id))).scalar()
        total_ka = db.execute(select(func.count(KnowledgeArticle.id))).scalar()

        print("\n" + "=" * 60)
        print("导入完成！")
        print(f"  经验帖总数: {total_posts}")
        print(f"  知识库文章总数: {total_ka}")
        print(f"  本次新增经验帖: {new_count}")
        print(f"  本次新增知识库文章: {ka_count}")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: 导入失败: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
