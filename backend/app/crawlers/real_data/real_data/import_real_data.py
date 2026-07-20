# -*- coding: utf-8 -*-
"""Import real articles from real_articles.json into the GradPath database.

Usage (inside Docker):
    docker exec gradpath-backend-1 python /app/app/crawlers/real_data/import_real_data.py

Or locally:
    cd backend
    python -m app.crawlers.real_data.import_real_data
"""
import sys, json, os, re
from pathlib import Path

# Add backend to path if running locally
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from app.database import Base, SessionLocal, engine
from app.models.user import User
from app.models.experience_post import ExperiencePost
from app.models.qa import QA
from app.models.qa_answer import QAAnswer
import uuid

SEED_USER_EMAIL = "kaoyan_seed@gradpath.local"
SEED_USER_NAME = "考研帮官方"

# Category mapping from article categories to ExperiencePost categories
CATEGORY_MAP = {
    "专业分析": "general",
    "择校指南": "general",
    "政策解读": "general",
    "考试技巧": "初试",
    "备考规划": "复习",
    "经验分享": "general",
    "复试经验": "复试",
    "心态调整": "general",
    "分数线": "初试",
    "调剂经验": "调剂",
    "调剂指南": "调剂",
    "备考经验": "复习",
    "备考方法": "复习",
}


def clean_content(raw):
    """Clean article content for database storage."""
    if not raw:
        return ""
    # Remove excessive CSS noise if present
    text = re.sub(r'\{[^}]*\}', '', raw)
    text = re.sub(r'/\*!.*?\*/', '', text)
    text = re.sub(r'--tw-[^:]+:[^;]+;', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    return text


def get_or_create_seed_user(db):
    """Get or create the seed user for crawled content."""
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
    """Get all existing source URLs from experience_posts."""
    stmt = select(ExperiencePost.source_url).where(
        ExperiencePost.source_url.isnot(None)
    )
    return {row[0] for row in db.execute(stmt).all()}


def get_existing_qa_urls(db):
    """Get all existing source URLs from QAs (stored in tags or title)."""
    stmt = select(QA.title)
    return {row[0] for row in db.execute(stmt).all()}


def import_articles(db, articles, existing_urls, seed_user):
    """Import articles as experience_posts. Returns count of new articles."""
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

        # Skip articles with too little content
        if len(content) < 50:
            content = f"{title}\n\n{content}\n\n原文链接: {url}"

        category_raw = article.get("category", "general")
        category = CATEGORY_MAP.get(category_raw, "general")

        # Create summary from first 200 chars
        summary = content[:200].replace("\n", " ").strip()
        if len(summary) > 197:
            summary = summary[:197] + "..."

        post = ExperiencePost(
            id=uuid.uuid4(),
            user_id=seed_user.id,
            title=title[:200],
            summary=summary,
            content=content,
            tags=[category_raw, "kaoyan.com"],
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


def generate_qa_from_articles(db, articles, existing_titles, seed_user):
    """Generate Q&A items from articles that are suitable for Q&A format."""
    qa_count = 0

    # Select articles that are Q&A suitable (adjustment guides, experience tips)
    qa_suitable = [
        a for a in articles
        if a.get("category") in ("调剂指南", "调剂经验", "备考经验", "考试技巧")
        and a.get("title") not in existing_titles
    ]

    for article in qa_suitable[:15]:  # Limit to 15 Q&A items
        title = article.get("title", "")
        content = article.get("content", "")
        url = article.get("url", "")

        if title in existing_titles:
            continue

        # Create a question based on the article title
        question_title = title.rstrip("！?。")
        if not question_title.endswith("？"):
            question_title += "？"

        question_content = f"想了解一下关于「{question_title}」的信息，请各位学长学姐分享经验。"
        answer_content = clean_content(content)[:3000]

        if len(answer_content) < 50:
            continue

        qa = QA(
            id=uuid.uuid4(),
            user_id=seed_user.id,
            title=question_title[:200],
            content=question_content,
            tags=[article.get("category", "general"), "kaoyan.com"],
            status="approved",
            view_count=0,
            answer_count=1,
            is_resolved=True,
        )
        db.add(qa)
        db.flush()

        answer = QAAnswer(
            id=uuid.uuid4(),
            qa_id=qa.id,
            user_id=seed_user.id,
            content=answer_content,
            is_best=True,
            like_count=0,
            status="approved",
        )
        db.add(answer)
        db.flush()

        qa.best_answer_id = answer.id
        existing_titles.add(title)
        qa_count += 1

    db.commit()
    return qa_count


def main():
    print("=" * 60)
    print("GradPath 真实考研数据导入脚本")
    print("=" * 60)

    # Ensure tables exist
    print("\n1. 检查数据库表...")
    Base.metadata.create_all(bind=engine)
    print("  ✓ 数据库表准备完成")

    # Load articles
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_articles.json")
    if not os.path.exists(json_path):
        print(f"\n✗ 文件不存在: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
    print(f"\n2. 加载文章数据: {len(articles)} 篇")

    db = SessionLocal()
    try:
        # Get or create seed user
        print("\n3. 准备种子用户...")
        seed_user = get_or_create_seed_user(db)

        # Get existing URLs to avoid duplicates
        existing_urls = get_existing_urls(db)
        print(f"  数据库中已有 {len(existing_urls)} 篇经验帖")

        # Import articles
        print("\n4. 导入经验帖...")
        new_count, skip_count = import_articles(db, articles, existing_urls, seed_user)
        print(f"  ✓ 新增 {new_count} 篇经验帖")
        print(f"  - 跳过 {skip_count} 篇（已存在）")

        # Generate Q&A items
        print("\n5. 生成问答数据...")
        existing_titles = get_existing_qa_urls(db)
        qa_count = generate_qa_from_articles(db, articles, existing_titles, seed_user)
        print(f"  ✓ 新增 {qa_count} 条问答")

        # Summary
        total_posts = db.execute(select(func.count(ExperiencePost.id))).scalar()
        total_qa = db.execute(select(func.count(QA.id))).scalar()

        print("\n" + "=" * 60)
        print("导入完成！统计信息：")
        print(f"  经验帖总数: {total_posts}")
        print(f"  问答总数: {total_qa}")
        print(f"  本次新增经验帖: {new_count}")
        print(f"  本次新增问答: {qa_count}")
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
