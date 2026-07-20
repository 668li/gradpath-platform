# -*- coding: utf-8 -*-
"""社交媒体数据导入脚本 — 将知乎和小红书数据导入GradPath数据库。

读取 zhihu_kaoyan.json 和 xiaohongshu_kaoyan.json，
导入 experience_posts 和 knowledge_articles 表。

Usage:
    cd D:\职业规划\职业规划\backend
    python -m app.crawlers.real_data.import_social
"""
import json
import os
import re
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(DATA_DIR, "..", "..", ".."))

from sqlalchemy import text
from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.experience_post import ExperiencePost
from app.models.knowledge_article import KnowledgeArticle


# ── 工具函数 ──────────────────────────────────────────────────────────

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  SKIP: {filename} not found")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  ERROR loading {filename}: {e}")
        return []


def safe_str(val, default=""):
    return str(val) if val is not None else default


def safe_int(val, default=0):
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def clean_content(raw, max_len=3000):
    """清理内容中的特殊字符。"""
    if not raw:
        return ""
    text = re.sub(r'\n{3,}', '\n\n', raw)
    text = text.strip()
    return text[:max_len] if len(text) > max_len else text


def get_system_user(db):
    """获取或创建系统用户。"""
    from uuid import UUID
    sid = UUID("00000000-0000-0000-0000-000000000000")
    user = db.query(User).filter(User.id == sid).first()
    if not user:
        user = User(
            id=sid,
            email="system@gradpath.com",
            name="系统",
            password_hash="",
        )
        db.add(user)
        db.commit()
        print("  创建系统用户")
    return user


# ── 主导入逻辑 ────────────────────────────────────────────────────────

def import_zhihu(db, user):
    """导入知乎数据到 experience_posts。"""
    print("\n--- 导入知乎数据 ---")
    data = load_json("zhihu_kaoyan.json")
    if not data:
        print("  无数据可导入")
        return 0, 0

    imported = 0
    skipped = 0

    for item in data:
        title = safe_str(item.get("title", ""))
        if not title:
            continue
        title = title[:200]

        # 去重：检查是否已存在相同标题
        existing = db.query(ExperiencePost).filter(
            ExperiencePost.title == title
        ).first()
        if existing:
            skipped += 1
            continue

        content = clean_content(item.get("content", ""))
        if len(content) < 50:
            skipped += 1
            continue

        tags = item.get("tags", ["考研"])
        if isinstance(tags, str):
            tags = [tags]

        # 根据标签推断分类
        category = "经验分享"
        for t in tags:
            if t in ("择校", "专业课复习", "公共课复习", "心态调整", "调剂", "复试", "时间规划"):
                category = t
                break

        upvotes = safe_int(item.get("upvotes", 0))
        author = safe_str(item.get("author", "匿名用户"))

        try:
            db.add(ExperiencePost(
                title=title,
                content=content,
                summary=content[:200],
                tags=tags,
                category=category,
                user_id=user.id,
                source_platform="zhihu",
                source_url=None,
                view_count=upvotes * 3,
                like_count=upvotes,
                comment_count=upvotes // 10,
                is_anonymous="匿名" in author,
                status="approved",
                is_verified=True,
            ))
            db.flush()
            imported += 1
        except Exception as e:
            db.rollback()
            skipped += 1
            print(f"  SKIP: {title[:50]}... - {e}")

    db.commit()
    print(f"  知乎: 新增 {imported}, 跳过 {skipped}")
    return imported, skipped


def import_xiaohongshu(db, user):
    """导入小红书数据到 experience_posts 和 knowledge_articles。"""
    print("\n--- 导入小红书数据 ---")
    data = load_json("xiaohongshu_kaoyan.json")
    if not data:
        print("  无数据可导入")
        return 0, 0

    imported_exp = 0
    imported_ka = 0
    skipped = 0

    for item in data:
        title = safe_str(item.get("title", ""))
        if not title:
            continue
        title = title[:200]

        content = clean_content(item.get("content", ""))
        if len(content) < 50:
            skipped += 1
            continue

        tags = item.get("tags", ["考研"])
        if isinstance(tags, str):
            tags = [tags]

        likes = safe_int(item.get("likes", 0))
        comments = safe_int(item.get("comments", 0))
        favorites = safe_int(item.get("favorites", 0))
        author = safe_str(item.get("author", "小红书用户"))

        # 50% 的内容导入 experience_posts，50% 导入 knowledge_articles
        # 这样可以同时丰富两个表的数据
        is_long_form = len(content) > 400 and imported_ka < 25

        # 去重检查
        existing_exp = db.query(ExperiencePost).filter(
            ExperiencePost.title == title
        ).first()
        existing_ka = db.query(KnowledgeArticle).filter(
            KnowledgeArticle.title == title
        ).first()
        if existing_exp or existing_ka:
            skipped += 1
            continue

        if is_long_form:
            # 导入 knowledge_articles
            category = "考研经验"
            for t in tags:
                if "调剂" in t:
                    category = "考研调剂"
                    break
                elif "复试" in t:
                    category = "考研复试"
                    break
                elif "数学" in t:
                    category = "考研数学"
                    break
                elif "英语" in t:
                    category = "考研英语"
                    break
                elif "政治" in t:
                    category = "考研政治"
                    break
                elif "择校" in t:
                    category = "考研择校"
                    break

            try:
                db.add(KnowledgeArticle(
                    title=title,
                    content=content,
                    category=category,
                    tags=tags + ["小红书"],
                    source="xiaohongshu",
                    metadata_={
                        "author": author,
                        "likes": likes,
                        "comments": comments,
                        "favorites": favorites,
                    },
                ))
                db.flush()
                imported_ka += 1
            except Exception as e:
                db.rollback()
                skipped += 1
                print(f"  SKIP KA: {title[:50]}... - {e}")
        else:
            # 导入 experience_posts
            category = "经验分享"
            for t in tags:
                if "调剂" in t:
                    category = "调剂"
                    break
                elif "复试" in t:
                    category = "复试"
                    break
                elif "数学" in t:
                    category = "复习"
                    break
                elif "英语" in t:
                    category = "复习"
                    break
                elif "政治" in t:
                    category = "复习"
                    break
                elif "择校" in t:
                    category = "择校"
                    break

            try:
                db.add(ExperiencePost(
                    title=title,
                    content=content,
                    summary=content[:200],
                    tags=tags + ["小红书"],
                    category=category,
                    user_id=user.id,
                    source_platform="xiaohongshu",
                    source_url=None,
                    view_count=likes * 5,
                    like_count=likes,
                    comment_count=comments,
                    is_anonymous=False,
                    status="approved",
                    is_verified=True,
                ))
                db.flush()
                imported_exp += 1
            except Exception as e:
                db.rollback()
                skipped += 1
                print(f"  SKIP EP: {title[:50]}... - {e}")

    db.commit()
    print(f"  小红书: experience_posts 新增 {imported_exp}, knowledge_articles 新增 {imported_ka}, 跳过 {skipped}")
    return imported_exp + imported_ka, skipped


def print_db_counts(db):
    """打印各表的数据量。"""
    print("\n=== 数据库统计 ===")
    tables = [
        ("experience_posts", "经验帖"),
        ("knowledge_articles", "知识文章"),
        ("schools", "院校"),
        ("qas", "问答"),
        ("qa_answers", "回答"),
    ]
    for table, label in tables:
        try:
            r = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = r.scalar()
            print(f"  {label:8s}: {count}")
        except Exception:
            pass

    # 社交媒体来源统计
    try:
        r = db.execute(text(
            "SELECT source_platform, COUNT(*) FROM experience_posts "
            "WHERE source_platform IN ('zhihu', 'xiaohongshu') "
            "GROUP BY source_platform"
        ))
        for row in r.fetchall():
            print(f"  {row[0]:8s}经验帖: {row[1]}")
    except Exception:
        pass

    try:
        r = db.execute(text(
            "SELECT source, COUNT(*) FROM knowledge_articles "
            "WHERE source = 'xiaohongshu' "
            "GROUP BY source"
        ))
        for row in r.fetchall():
            print(f"  {row[0]:8s}知识文章: {row[1]}")
    except Exception:
        pass


def main():
    print("=" * 60)
    print("GradPath 社交媒体数据导入")
    print("知乎 + 小红书 → experience_posts + knowledge_articles")
    print("=" * 60)

    # 确保表存在
    print("\n1. 检查数据库表...")
    Base.metadata.create_all(bind=engine)
    print("  数据库表准备完成")

    db = SessionLocal()
    try:
        # 获取系统用户
        print("\n2. 获取系统用户...")
        user = get_system_user(db)

        # 导入知乎数据
        print("\n3. 导入知乎数据...")
        zhihu_count, zhihu_skip = import_zhihu(db, user)

        # 导入小红书数据
        print("\n4. 导入小红书数据...")
        xhs_count, xhs_skip = import_xiaohongshu(db, user)

        # 打印数据库统计
        print_db_counts(db)

        # 总结
        print("\n" + "=" * 60)
        print(f"导入完成!")
        print(f"  知乎: 新增 {zhihu_count}, 跳过 {zhihu_skip}")
        print(f"  小红书: 新增 {xhs_count}, 跳过 {xhs_skip}")
        print(f"  总计: 新增 {zhihu_count + xhs_count}, 跳过 {zhihu_skip + xhs_skip}")
        print("=" * 60)

    except Exception as e:
        print(f"\n导入失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
