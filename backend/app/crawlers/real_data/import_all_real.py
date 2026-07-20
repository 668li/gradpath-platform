# -*- coding: utf-8 -*-
"""Unified import script for ALL real scraped data into GradPath database.

Reads all available JSON files, deduplicates, and imports into:
- experience_posts (source_platform='crawler')
- knowledge_articles
- schools

Usage (inside Docker):
    docker exec gradpath-backend-1 python /app/app/crawlers/real_data/import_all_real.py
"""
import sys
import json
import os
import re
import uuid
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from app.database import Base, SessionLocal, engine
from app.models.user import User
from app.models.experience_post import ExperiencePost
from app.models.knowledge_article import KnowledgeArticle
from app.models.school import School

SEED_USER_EMAIL = "realdata_seed@gradpath.local"
SEED_USER_NAME = "真实数据采集"

CATEGORY_MAP = {
    "专业分析": "general",
    "择校指南": "general",
    "择校": "择校",
    "政策解读": "general",
    "政策": "general",
    "考试技巧": "初试",
    "备考规划": "复习",
    "备考": "复习",
    "经验分享": "general",
    "复试经验": "复试",
    "复试": "复试",
    "心态调整": "general",
    "分数线": "初试",
    "调剂经验": "调剂",
    "调剂指南": "调剂",
    "备考经验": "复习",
    "备考方法": "复习",
    "初试": "初试",
    "专业": "general",
    "院校": "择校",
    "复习": "复习",
}

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def clean_content(raw):
    if not raw:
        return ""
    text = re.sub(r'\{[^}]*\}', '', raw)
    text = re.sub(r'/\*!.*?\*/', '', text)
    text = re.sub(r'--tw-[^:]+:[^;]+;', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
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
    print(f"  Created seed user: {SEED_USER_NAME}")
    return user


def load_json_file(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  [SKIP] {filename} not found")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  [OK] Loaded {filename}")
        return data
    except Exception as e:
        print(f"  [ERROR] {filename}: {e}")
        return None


def load_all_data():
    sources = {}
    sources["real_articles"] = load_json_file("real_articles.json")
    sources["firecrawl"] = load_json_file("firecrawl_scraped.json")
    sources["kaoyan"] = load_json_file("kaoyan_real_data.json")
    sources["yanzhao"] = load_json_file("yanzhao_real_data.json")
    sources["scorelines"] = load_json_file("scorelines_real_data.json")
    sources["scraped_data"] = load_json_file("scraped_data.json")
    return sources


def normalize_article(raw, source_tag):
    title = raw.get("title", "").strip()
    url = raw.get("url", "")
    content = clean_content(raw.get("content", ""))
    category_raw = raw.get("category", "经验分享")
    category = CATEGORY_MAP.get(category_raw, "general")
    summary = content[:200].replace("\n", " ").strip()
    if len(summary) > 197:
        summary = summary[:197] + "..."

    if len(content) < 50:
        content = f"{title}\n\n{content}"
    if url:
        content = content + f"\n\n原文链接: {url}"

    return {
        "title": title[:200],
        "url": url,
        "content": content,
        "summary": summary,
        "tags": [category_raw, source_tag],
        "category": category,
        "source": raw.get("source", ""),
        "scraped_at": raw.get("scraped_at", ""),
    }


def collect_all_articles(sources):
    articles = []
    seen_urls = set()

    if sources["real_articles"]:
        for a in sources["real_articles"]:
            url = a.get("url", "")
            if url and url in seen_urls:
                continue
            seen_urls.add(url)
            articles.append(normalize_article(a, "kaoyan.com"))

    if sources["firecrawl"] and isinstance(sources["firecrawl"], dict):
        for a in sources["firecrawl"].get("articles", []):
            url = a.get("url", "")
            if url and url in seen_urls:
                continue
            seen_urls.add(url)
            articles.append(normalize_article(a, "firecrawl"))

    if sources["kaoyan"] and isinstance(sources["kaoyan"], dict):
        for a in sources["kaoyan"].get("experience_posts", []):
            title = a.get("title", "")
            content = a.get("content", "")
            university = a.get("university", "")
            major = a.get("major", "")
            author = a.get("author", "")
            score = a.get("score", "")
            year = a.get("year", "")

            full_content = content
            if university:
                full_content = f"院校: {university}\n专业: {major}\n\n{content}"
            if score:
                full_content += f"\n\n初试分数: {score}"
            if year:
                full_content += f"\n年份: {year}"

            articles.append({
                "title": title[:200],
                "url": f"kaoyan_seed_{uuid.uuid4().hex[:8]}",
                "content": full_content,
                "summary": content[:200].replace("\n", " ").strip(),
                "tags": ["经验分享", "kaoyan.com", university, major],
                "category": "general",
                "source": "kaoyan.com",
                "scraped_at": "",
            })

    return articles


def import_experience_posts(db, articles, existing_urls, seed_user):
    new_count = 0
    skip_count = 0

    for article in articles:
        url = article["url"]
        title = article["title"]

        if url and url in existing_urls:
            skip_count += 1
            continue
        if not title:
            skip_count += 1
            continue

        post = ExperiencePost(
            id=uuid.uuid4(),
            user_id=seed_user.id,
            title=title,
            summary=article.get("summary", ""),
            content=article.get("content", ""),
            tags=article.get("tags", []),
            category=article.get("category", "general"),
            view_count=0,
            like_count=0,
            comment_count=0,
            external_view_count=0,
            external_like_count=0,
            is_pinned=False,
            is_anonymous=False,
            status="approved",
            source_platform="crawler",
            source_url=url if url else None,
            is_verified=True,
        )
        db.add(post)
        if url:
            existing_urls.add(url)
        new_count += 1

    db.commit()
    return new_count, skip_count


def import_knowledge_articles(db, sources, existing_ka_urls):
    new_count = 0

    if sources["firecrawl"] and isinstance(sources["firecrawl"], dict):
        for a in sources["firecrawl"].get("articles", []):
            url = a.get("url", "")
            title = a.get("title", "")
            content = clean_content(a.get("content", ""))
            category_raw = a.get("category", "")

            if url in existing_ka_urls or len(content) < 100:
                continue

            ka = KnowledgeArticle(
                id=uuid.uuid4(),
                category="education_path",
                title=title[:200],
                content=content[:10000],
                tags=[category_raw, "考研", "firecrawl"],
                source=url,
                metadata_={
                    "source_site": a.get("source", ""),
                    "scraped_at": a.get("scraped_at", ""),
                },
                is_published=True,
            )
            db.add(ka)
            existing_ka_urls.add(url)
            new_count += 1

    if sources["scorelines"] and isinstance(sources["scorelines"], dict):
        national_lines = sources["scorelines"].get("national_lines", [])
        university_lines = sources["scorelines"].get("university_lines", [])

        all_lines = national_lines + university_lines
        if all_lines:
            content_parts = ["# 考研分数线汇总\n"]
            for line in all_lines[:200]:
                source = line.get("source", "")
                year = line.get("year", "")
                major = line.get("major", "")
                total = line.get("total", "")
                politics = line.get("politics", "")
                english = line.get("english", "")
                degree_type = line.get("degree_type", "")

                parts = [f"## {source} {year}年 {degree_type} {major}"]
                parts.append(f"总分: {total}  政治: {politics}  英语: {english}")
                content_parts.append("\n".join(parts))

            ka = KnowledgeArticle(
                id=uuid.uuid4(),
                category="education_path",
                title="考研分数线汇总（国家线+高校自划线）",
                content="\n\n".join(content_parts)[:10000],
                tags=["分数线", "国家线", "考研"],
                source="scorelines_real_data.json",
                metadata_={
                    "total_lines": len(all_lines),
                    "years": sources["scorelines"].get("metadata", {}).get("years_covered", []),
                },
                is_published=True,
            )
            db.add(ka)
            new_count += 1

    if sources["kaoyan"] and isinstance(sources["kaoyan"], dict):
        qa_list = sources["kaoyan"].get("qa", [])
        for qa in qa_list[:20]:
            question = qa.get("question", "")
            answer = qa.get("answer", "")
            if not question or not answer:
                continue

            content = f"问: {question}\n\n答: {answer}"
            ka = KnowledgeArticle(
                id=uuid.uuid4(),
                category="education_path",
                title=question[:200],
                content=content[:10000],
                tags=["问答", "考研", "kaoyan.com"],
                source=f"kaoyan_qa_{uuid.uuid4().hex[:8]}",
                metadata_={"source_site": "kaoyan.com"},
                is_published=True,
            )
            db.add(ka)
            new_count += 1

    db.commit()
    return new_count


def import_schools(db, sources, existing_school_names):
    new_count = 0

    if sources["yanzhao"] and isinstance(sources["yanzhao"], dict):
        for uni in sources["yanzhao"].get("universities", []):
            name = uni.get("name", "").strip()
            if not name or name in existing_school_names:
                continue

            province = uni.get("province", "")
            level = uni.get("type", "")
            majors_list = uni.get("majors", [])

            key_majors = [m.get("name", "") for m in majors_list[:10]]

            slug = re.sub(r'[^\w\u4e00-\u9fff]', '', name)[:50]

            school = School(
                id=uuid.uuid4(),
                name=name,
                slug=slug,
                province=province,
                level=level,
                key_majors=key_majors if key_majors else None,
            )
            db.add(school)
            existing_school_names.add(name)
            new_count += 1

    db.commit()
    return new_count


def main():
    print("=" * 60)
    print("GradPath 全量真实数据导入脚本")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)

    print("\n1. 检查数据库表...")
    Base.metadata.create_all(bind=engine)
    print("  OK 数据库表准备完成")

    print("\n2. 加载所有JSON数据文件...")
    sources = load_all_data()

    total_json_items = 0
    for key, data in sources.items():
        if data is None:
            continue
        if isinstance(data, list):
            total_json_items += len(data)
        elif isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    total_json_items += len(v)
    print(f"\n  JSON文件中共加载 {total_json_items} 条原始记录")

    db = SessionLocal()
    try:
        print("\n3. 准备种子用户...")
        seed_user = get_or_create_seed_user(db)

        print("\n4. 去重并合并经验帖...")
        articles = collect_all_articles(sources)
        print(f"  去重后共 {len(articles)} 篇经验帖/文章")

        existing_urls = set()
        stmt = select(ExperiencePost.source_url).where(ExperiencePost.source_url.isnot(None))
        existing_urls = {row[0] for row in db.execute(stmt).all()}
        print(f"  数据库已有 {len(existing_urls)} 篇经验帖")

        print("\n5. 导入经验帖到 experience_posts...")
        new_posts, skip_posts = import_experience_posts(db, articles, existing_urls, seed_user)
        print(f"  OK 新增 {new_posts} 篇经验帖")
        print(f"  - 跳过 {skip_posts} 篇（已存在或无效）")

        print("\n6. 导入知识库文章到 knowledge_articles...")
        stmt_ka = select(KnowledgeArticle.source).where(KnowledgeArticle.source.isnot(None))
        existing_ka_urls = {row[0] for row in db.execute(stmt_ka).all()}
        new_ka = import_knowledge_articles(db, sources, existing_ka_urls)
        print(f"  OK 新增 {new_ka} 篇知识库文章")

        print("\n7. 导入院校数据到 schools...")
        stmt_school = select(School.name)
        existing_school_names = {row[0] for row in db.execute(stmt_school).all()}
        new_schools = import_schools(db, sources, existing_school_names)
        print(f"  OK 新增 {new_schools} 所院校")

        total_posts = db.execute(select(func.count(ExperiencePost.id))).scalar()
        total_ka = db.execute(select(func.count(KnowledgeArticle.id))).scalar()
        total_schools = db.execute(select(func.count(School.id))).scalar()

        print("\n" + "=" * 60)
        print("导入完成！最终统计：")
        print(f"  experience_posts 总数: {total_posts}")
        print(f"  knowledge_articles 总数: {total_ka}")
        print(f"  schools 总数: {total_schools}")
        print(f"  本次新增经验帖: {new_posts}")
        print(f"  本次新增知识库文章: {new_ka}")
        print(f"  本次新增院校: {new_schools}")
        print("=" * 60)

        print("\n验证SQL:")
        print("  SELECT source_platform, COUNT(*) FROM experience_posts GROUP BY source_platform;")
        print("  SELECT COUNT(*) FROM knowledge_articles;")
        print("  SELECT COUNT(*) FROM schools;")

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
