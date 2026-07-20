# -*- coding: utf-8 -*-
"""统一导入所有真实爬取数据到GradPath数据库"""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
from sqlalchemy import text

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(DATA_DIR, '..', '..', '..'))

from app.database import SessionLocal, engine
from app.models.user import User
from app.models.experience_post import ExperiencePost
from app.models.knowledge_article import KnowledgeArticle
from app.models.school import School

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  SKIP: {filename} not found")
        return []
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
            data = json.load(f)
        return data if isinstance(data, list) else []
    except:
        return []

def extract_text_from_markdown(md, max_len=3000):
    """从Markdown提取纯文本"""
    import re
    text = re.sub(r'!\[.*?\]\(.*?\)', '', md)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text[:max_len] if len(text) > max_len else text

def ensure_system_user(db):
    from uuid import UUID
    sid = UUID("00000000-0000-0000-0000-000000000000")
    user = db.query(User).filter(User.id == sid).first()
    if not user:
        user = User(id=sid, email="system@gradpath.local", name="系统", password_hash="")
        db.add(user)
        db.commit()
    return user

def import_all():
    db = SessionLocal()
    try:
        user = ensure_system_user(db)
        total_imported = 0
        total_skipped = 0
        
        # === 1. Import from real_articles.json ===
        print("\n1. real_articles.json...")
        articles = load_json("real_articles.json")
        for art in articles:
            title = art.get("title", "")
            url = art.get("url", "")
            if not title:
                continue
            existing = db.query(ExperiencePost).filter(ExperiencePost.title == title).first()
            if existing:
                total_skipped += 1
                continue
            content = art.get("content", "")
            if len(content) > 2000:
                content = extract_text_from_markdown(content)
            db.add(ExperiencePost(
                title=title, content=content, summary=art.get("summary", title[:100]),
                tags=[art.get("category", "")], category=art.get("category", "经验"),
                user_id=user.id, source_platform="crawler",
                view_count=500, like_count=30,
            ))
            total_imported += 1
        db.commit()
        print(f"  Imported: {total_imported}, Skipped: {total_skipped}")
        
        # === 2. Import from kaoyan_crawled.json (100 pages) ===
        print("\n2. kaoyan_crawled.json...")
        crawled = load_json("kaoyan_crawled.json")
        imported_before = total_imported
        for page in crawled:
            if isinstance(page, dict):
                title = page.get("title", "") or page.get("metadata", {}).get("title", "")
                content = page.get("markdown", "") or page.get("content", "")
            else:
                continue
            if not title or not content or len(content) < 100:
                continue
            title = title[:200]
            existing = db.query(ExperiencePost).filter(ExperiencePost.title == title).first()
            if existing:
                total_skipped += 1
                continue
            clean = extract_text_from_markdown(content)
            if len(clean) < 50:
                total_skipped += 1
                continue
            db.add(ExperiencePost(
                title=title, content=clean, summary=clean[:200],
                tags=["考研"], category="综合",
                user_id=user.id, source_platform="crawler",
                view_count=300, like_count=20,
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")
        
        # === 3. Import from yz_crawled.json (75 pages) ===
        print("\n3. yz_crawled.json...")
        yz_data = load_json("yz_crawled.json")
        imported_before = total_imported
        if isinstance(yz_data, dict):
            for section, pages in yz_data.get("data", {}).items():
                if not isinstance(pages, list):
                    continue
                for page in pages:
                    url = page.get("url", "")
                    content = page.get("content", "")
                    if not content or len(content) < 100:
                        continue
                    # Use URL for dedup instead of title (title is often generic)
                    existing = db.query(KnowledgeArticle).filter(
                        KnowledgeArticle.title == url[:200]
                    ).first()
                    if existing:
                        total_skipped += 1
                        continue
                    clean = extract_text_from_markdown(content)
                    if len(clean) < 50:
                        continue
                    # Extract actual title from content if possible
                    title_line = clean.split('\n')[0][:200] if clean else url[:200]
                    db.add(KnowledgeArticle(
                        title=title_line or url[:200], content=clean, category="研招网资讯",
                        tags=[section], source="yz.chsi.com.cn",
                    ))
                    total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")
        
        # === 4. Import from webfetch_articles.json (50 articles) ===
        print("\n4. webfetch_articles.json...")
        webfetch = load_json("webfetch_articles.json")
        imported_before = total_imported
        for art in webfetch:
            title = art.get("title", "")
            content = art.get("content", "")
            if not title or not content or len(content) < 100:
                continue
            title = title[:200]
            existing = db.query(ExperiencePost).filter(ExperiencePost.title == title).first()
            if existing:
                total_skipped += 1
                continue
            clean = extract_text_from_markdown(content)
            if len(clean) < 50:
                continue
            db.add(ExperiencePost(
                title=title, content=clean, summary=clean[:200],
                tags=["考研"], category="经验分享",
                user_id=user.id, source_platform="crawler",
                view_count=400, like_count=25,
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")
        
        # === 5. Import bilibili_data.json as knowledge articles ===
        print("\n5. bilibili_data.json...")
        bili_raw = load_json("bilibili_data.json")
        # Handle dict structure with 'videos' key
        if isinstance(bili_raw, dict) and "videos" in bili_raw:
            bili = bili_raw["videos"]
        elif isinstance(bili_raw, list):
            bili = bili_raw
        else:
            bili = []
        imported_before = total_imported
        for vid in bili:
            title = vid.get("title", "")
            desc = vid.get("description", "")
            url = vid.get("url", "")
            views = vid.get("views", 0)
            if not title:
                continue
            existing = db.query(KnowledgeArticle).filter(KnowledgeArticle.title == title[:200]).first()
            if existing:
                total_skipped += 1
                continue
            content = f"视频标题: {title}\n作者: {vid.get('author', 'N/A')}\n播放量: {views}\n简介: {desc}\n链接: {url}"
            db.add(KnowledgeArticle(
                title=title[:200], content=content[:3000], category="B站考研视频",
                tags=[vid.get("keyword", "考研")], source="bilibili.com",
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")
        
        # === Final counts ===
        print("\n=== FINAL DB COUNTS ===")
        tables = [
            ("experience_posts", "经验帖"),
            ("knowledge_articles", "知识文章"),
            ("schools", "院校"),
            ("qas", "问答"),
            ("qa_answers", "回答"),
            ("dark_knowledge", "暗知识"),
            ("grad_school_intel", "院校情报"),
            ("grad_scoreline_records", "分数线"),
            ("companies", "公司"),
            ("salary_benchmarks", "薪资基准"),
        ]
        for table, label in tables:
            try:
                r = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                print(f"  {label:8s}: {r.scalar()}")
            except:
                pass
        
        # Crawler source count
        try:
            r = db.execute(text("SELECT COUNT(*) FROM experience_posts WHERE source_platform='crawler'"))
            print(f"\n  真实爬取经验帖: {r.scalar()}")
        except:
            pass
        
        print(f"\n  本次导入: {total_imported} 条")
        print(f"  跳过(重复): {total_skipped} 条")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("="*50)
    print("统一导入所有真实爬取数据")
    print("="*50)
    import_all()
    print("\n完成!")
