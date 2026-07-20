# -*- coding: utf-8 -*-
"""一键导入batch_scrape_results.json到数据库"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = "/app/app/crawlers/real_data"
sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.models.user import User
from app.models.experience_post import ExperiencePost
from app.models.knowledge_article import KnowledgeArticle
from uuid import UUID

def main():
    db = SessionLocal()
    try:
        # Load batch results
        with open(os.path.join(DATA_DIR, "batch_scrape_results.json"), 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get system user
        sid = UUID("00000000-0000-0000-0000-000000000000")
        user = db.query(User).filter(User.id == sid).first()
        if not user:
            user = User(id=sid, email="system@gradpath.local", name="系统", password_hash="")
            db.add(user)
            db.commit()
        
        imported = 0
        skipped = 0
        
        # Import kaoyan articles as experience_posts
        for item in data.get("kaoyan", []):
            content = item.get("content", "")
            if len(content) < 100:
                skipped += 1
                continue
            title = content[:100].split(".")[0].strip() if content else ""
            if not title:
                title = f"kaoyan_article_{imported}"
            existing = db.query(ExperiencePost).filter(ExperiencePost.title == title).first()
            if existing:
                skipped += 1
                continue
            db.add(ExperiencePost(
                title=title, content=content[:3000], summary=content[:200],
                tags=["考研", "经验"], category="爬取数据",
                user_id=user.id, source_platform="crawler",
                view_count=200, like_count=15,
            ))
            imported += 1
        
        # Import yz articles as knowledge_articles
        for item in data.get("yz", []):
            content = item.get("content", "")
            if len(content) < 100:
                skipped += 1
                continue
            title = content[:100].strip()
            if not title:
                title = f"yz_article_{imported}"
            existing = db.query(KnowledgeArticle).filter(KnowledgeArticle.title == title).first()
            if existing:
                skipped += 1
                continue
            db.add(KnowledgeArticle(
                title=title, content=content[:3000], category="研招网资讯",
                tags=["考研", "政策"], source="yz.chsi.com.cn",
            ))
            imported += 1
        
        db.commit()
        print(f"Imported: {imported}, Skipped: {skipped}")
        
        # Final counts
        from sqlalchemy import text
        tables = [("experience_posts", "经验帖"), ("knowledge_articles", "知识文章"), ("schools", "院校"),
                  ("qas", "问答"), ("qa_answers", "回答"), ("dark_knowledge", "暗知识"),
                  ("grad_school_intel", "院校情报"), ("grad_scoreline_records", "分数线"),
                  ("companies", "公司"), ("salary_benchmarks", "薪资基准")]
        total = 0
        for t, l in tables:
            r = db.execute(text(f"SELECT COUNT(*) FROM {t}"))
            c = r.scalar()
            total += c
            print(f"{l}: {c}")
        print(f"\nTotal: {total}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
