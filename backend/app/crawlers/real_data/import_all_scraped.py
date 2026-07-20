# -*- coding: utf-8 -*-
"""统一导入所有真实爬取数据到GradPath数据库"""
import sys, os, json, time, re
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
        return None
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"  ERROR loading {filename}: {e}")
        return None

def load_json_as_list(filename):
    data = load_json(filename)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ['articles', 'videos', 'data', 'majors']:
            if key in data and isinstance(data[key], list):
                return data[key]
        if 'sections' in data:
            pages = []
            for section, section_data in data['sections'].items():
                if isinstance(section_data, dict) and 'pages' in section_data:
                    for p in section_data['pages']:
                        p['section'] = section
                        pages.append(p)
            return pages
    return []

def extract_text_from_markdown(md, max_len=3000):
    text = re.sub(r'!\[.*?\]\(.*?\)', '', md)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text[:max_len] if len(text) > max_len else text

def strip_css_js(text):
    """Strip CSS and JS from raw HTML content."""
    text = re.sub(r':root\s*\{[^}]*\}', '', text)
    text = re.sub(r'\.[\w.-]+\s*\{[^}]*\}', '', text)
    text = re.sub(r'[\w.-]+\s*\{[^}]*\}', '', text)
    text = re.sub(r'--[\w-]+:\s*[^;]+;', '', text)
    text = re.sub(r'[\w-]+:\s*[^;}{]+;', '', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def ensure_system_user(db):
    from uuid import UUID
    sid = UUID("00000000-0000-0000-0000-000000000000")
    user = db.query(User).filter(User.id == sid).first()
    if not user:
        user = User(id=sid, email="system@gradpath.local", name="系统", password_hash="")
        db.add(user)
        db.commit()
    return user

def safe_str(val, default=""):
    if val is None:
        return default
    return str(val)

def safe_int(val, default=0):
    if val is None:
        return default
    try:
        return int(val)
    except:
        return default

def import_all():
    db = SessionLocal()
    try:
        user = ensure_system_user(db)
        total_imported = 0
        total_skipped = 0

        # === 1. real_articles.json (经验帖) ===
        print("\n1. real_articles.json...")
        data = load_json("real_articles.json")
        items = data if isinstance(data, list) else []
        imported_before = total_imported
        for art in items:
            title = safe_str(art.get("title", ""))
            if not title:
                continue
            existing = db.query(ExperiencePost).filter(ExperiencePost.title == title[:200]).first()
            if existing:
                total_skipped += 1
                continue
            content = safe_str(art.get("content", ""))
            if len(content) > 2000:
                content = extract_text_from_markdown(content)
            db.add(ExperiencePost(
                title=title[:200], content=content[:3000],
                summary=safe_str(art.get("summary", ""))[:500] or title[:100],
                tags=[art.get("category", "")], category=art.get("category", "经验"),
                user_id=user.id, source_platform="crawler",
                view_count=500, like_count=30,
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 2. kaoyan_crawled.json ===
        print("\n2. kaoyan_crawled.json...")
        crawled = load_json_as_list("kaoyan_crawled.json")
        imported_before = total_imported
        for page in crawled:
            if not isinstance(page, dict):
                continue
            title = safe_str(page.get("title", "")) or safe_str(page.get("metadata", {}).get("title", ""))
            content = safe_str(page.get("markdown", "")) or safe_str(page.get("content", ""))
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
                title=title, content=clean[:3000], summary=clean[:200],
                tags=["考研"], category="综合",
                user_id=user.id, source_platform="crawler",
                view_count=300, like_count=20,
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 3. yz_crawled.json ===
        print("\n3. yz_crawled.json...")
        yz_data = load_json("yz_crawled.json")
        imported_before = total_imported
        if isinstance(yz_data, dict):
            for section, pages in yz_data.get("data", {}).items():
                if not isinstance(pages, list):
                    continue
                for page in pages:
                    url = safe_str(page.get("url", ""))
                    content = safe_str(page.get("content", ""))
                    if not content or len(content) < 100:
                        continue
                    existing = db.query(KnowledgeArticle).filter(
                        KnowledgeArticle.title == url[:200]
                    ).first()
                    if existing:
                        total_skipped += 1
                        continue
                    clean = extract_text_from_markdown(content)
                    if len(clean) < 50:
                        continue
                    title_line = clean.split('\n')[0][:200] if clean else url[:200]
                    db.add(KnowledgeArticle(
                        title=title_line or url[:200], content=clean[:3000],
                        category="研招网资讯", tags=[section], source="yz.chsi.com.cn",
                    ))
                    total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 4. webfetch_articles.json ===
        print("\n4. webfetch_articles.json...")
        webfetch = load_json_as_list("webfetch_articles.json")
        imported_before = total_imported
        for art in webfetch:
            title = safe_str(art.get("title", ""))
            content = safe_str(art.get("content", ""))
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
                title=title, content=clean[:3000], summary=clean[:200],
                tags=["考研"], category="经验分享",
                user_id=user.id, source_platform="crawler",
                view_count=400, like_count=25,
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 5. bilibili_data.json ===
        print("\n5. bilibili_data.json...")
        bili = load_json_as_list("bilibili_data.json")
        imported_before = total_imported
        for vid in bili:
            if not isinstance(vid, dict):
                continue
            title = safe_str(vid.get("title", ""))
            if not title:
                continue
            existing = db.query(KnowledgeArticle).filter(KnowledgeArticle.title == title[:200]).first()
            if existing:
                total_skipped += 1
                continue
            desc = safe_str(vid.get("description", ""))
            url = safe_str(vid.get("url", ""))
            views = safe_int(vid.get("views", 0))
            content = f"视频标题: {title}\n作者: {vid.get('author', 'N/A')}\n播放量: {views}\n简介: {desc}\n链接: {url}"
            db.add(KnowledgeArticle(
                title=title[:200], content=content[:3000], category="B站考研视频",
                tags=[vid.get("keyword", "考研")], source="bilibili.com",
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 6. kaoyan_round2.json (60 articles) ===
        print("\n6. kaoyan_round2.json...")
        kaoyan2 = load_json_as_list("kaoyan_round2.json")
        imported_before = total_imported
        for art in kaoyan2:
            if not isinstance(art, dict):
                continue
            title = safe_str(art.get("title", ""))
            if not title:
                continue
            title = title[:200]
            existing = db.query(ExperiencePost).filter(ExperiencePost.title == title).first()
            if existing:
                total_skipped += 1
                continue
            content = safe_str(art.get("content", ""))
            clean = extract_text_from_markdown(content) if len(content) > 2000 else content
            if len(clean) < 50:
                total_skipped += 1
                continue
            category = art.get("category", "考研")
            db.add(ExperiencePost(
                title=title, content=clean[:3000], summary=clean[:200],
                tags=[category], category=category,
                user_id=user.id, source_platform="crawler",
                source_url=safe_str(art.get("url", "")),
                view_count=300, like_count=20,
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 7. yz_round2.json (62 pages) ===
        print("\n7. yz_round2.json...")
        yz2 = load_json("yz_round2.json")
        imported_before = total_imported
        if isinstance(yz2, dict):
            for section_name, section_data in yz2.get("sections", {}).items():
                if not isinstance(section_data, dict):
                    continue
                pages = section_data.get("pages", [])
                for page in pages:
                    if not isinstance(page, dict):
                        continue
                    content = safe_str(page.get("markdown", "")) or safe_str(page.get("content", ""))
                    if not content or len(content) < 100:
                        continue
                    url = safe_str(page.get("url", ""))
                    existing = db.query(KnowledgeArticle).filter(
                        KnowledgeArticle.title == url[:200]
                    ).first()
                    if existing:
                        total_skipped += 1
                        continue
                    clean = extract_text_from_markdown(content)
                    if len(clean) < 50:
                        continue
                    title_line = safe_str(page.get("title", ""))[:200] or clean.split('\n')[0][:200] or url[:200]
                    db.add(KnowledgeArticle(
                        title=title_line, content=clean[:3000],
                        category="研招网资讯", tags=[section_name],
                        source="yz.chsi.com.cn",
                    ))
                    total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 8. webfetch_round2.json (50 articles) ===
        print("\n8. webfetch_round2.json...")
        wf2_data = load_json("webfetch_round2.json")
        imported_before = total_imported
        if isinstance(wf2_data, dict) and "articles" in wf2_data:
            for art in wf2_data["articles"]:
                title = safe_str(art.get("title", ""))
                content = safe_str(art.get("content", ""))
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
                source = art.get("source", "kaoyan.com")
                db.add(ExperiencePost(
                    title=title, content=clean[:3000], summary=clean[:200],
                    tags=["考研"], category="考研攻略",
                    user_id=user.id, source_platform="crawler",
                    source_url=safe_str(art.get("url", "")),
                    view_count=350, like_count=22,
                ))
                total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 9. webfetch_round3.json (30 articles) ===
        print("\n9. webfetch_round3.json...")
        wf3_data = load_json("webfetch_round3.json")
        imported_before = total_imported
        if isinstance(wf3_data, dict) and "articles" in wf3_data:
            for art in wf3_data["articles"]:
                title = safe_str(art.get("title", ""))
                content = safe_str(art.get("content", ""))
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
                tags = art.get("tags", ["考研"])
                if isinstance(tags, str):
                    tags = [tags]
                db.add(ExperiencePost(
                    title=title, content=clean[:3000], summary=clean[:200],
                    tags=tags, category="备考经验",
                    user_id=user.id, source_platform="crawler",
                    view_count=350, like_count=22,
                ))
                total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 10. koolearn_crawled.json (46 pages) ===
        print("\n10. koolearn_crawled.json...")
        kool = load_json("koolearn_crawled.json")
        imported_before = total_imported
        if isinstance(kool, dict) and "data" in kool:
            for page in kool["data"]:
                if not isinstance(page, dict):
                    continue
                title = safe_str(page.get("title", ""))
                content = safe_str(page.get("markdown", "")) or safe_str(page.get("content", ""))
                if not title or not content or len(content) < 100:
                    continue
                title = title[:200]
                existing = db.query(ExperiencePost).filter(ExperiencePost.title == title).first()
                if existing:
                    total_skipped += 1
                    continue
                existing_ka = db.query(KnowledgeArticle).filter(KnowledgeArticle.title == title).first()
                if existing_ka:
                    total_skipped += 1
                    continue
                clean = extract_text_from_markdown(content)
                if len(clean) < 50:
                    continue
                url = safe_str(page.get("url", ""))
                if "kaoyan.koolearn.com" in url:
                    db.add(KnowledgeArticle(
                        title=title, content=clean[:3000],
                        category="考研资讯", tags=["新东方考研"],
                        source="koolearn.com",
                    ))
                else:
                    db.add(ExperiencePost(
                        title=title, content=clean[:3000], summary=clean[:200],
                        tags=["考研"], category="考研资讯",
                        user_id=user.id, source_platform="crawler",
                        source_url=url,
                        view_count=300, like_count=18,
                    ))
                total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 11. bilibili_round2.json (50 videos) ===
        print("\n11. bilibili_round2.json...")
        bili2 = load_json_as_list("bilibili_round2.json")
        imported_before = total_imported
        for vid in bili2:
            if not isinstance(vid, dict):
                continue
            title = safe_str(vid.get("title", ""))
            if not title:
                continue
            title = title[:200]
            existing = db.query(KnowledgeArticle).filter(KnowledgeArticle.title == title).first()
            if existing:
                total_skipped += 1
                continue
            desc = safe_str(vid.get("description", ""))
            url = safe_str(vid.get("url", ""))
            views = safe_int(vid.get("views", 0))
            author = safe_str(vid.get("author", ""))
            keyword = safe_str(vid.get("keyword", "考研"))
            content = f"视频标题: {title}\n作者: {author}\n播放量: {views}\n简介: {desc}\n链接: {url}"
            db.add(KnowledgeArticle(
                title=title, content=content[:3000], category="B站考研视频",
                tags=[keyword], source="bilibili.com",
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 12. adjust_crawled.json (30 items) ===
        print("\n12. adjust_crawled.json...")
        adjust_data = load_json("adjust_crawled.json")
        imported_before = total_imported
        if isinstance(adjust_data, dict) and "pages" in adjust_data:
            for page_key, page_data in adjust_data["pages"].items():
                if not isinstance(page_data, dict):
                    continue
                items = page_data.get("items", [])
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    title = safe_str(item.get("title", ""))
                    if not title:
                        continue
                    title = title[:200]
                    existing = db.query(KnowledgeArticle).filter(
                        KnowledgeArticle.title == title
                    ).first()
                    if existing:
                        total_skipped += 1
                        continue
                    date = safe_str(item.get("date", ""))
                    content = f"调剂信息: {title}\n日期: {date}\n分类: {page_data.get('description', page_key)}"
                    db.add(KnowledgeArticle(
                        title=title, content=content[:3000],
                        category="考研调剂", tags=["调剂", page_key],
                        source="kaoyan.com",
                    ))
                    total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 13. college_details.json (30 colleges) ===
        print("\n13. college_details.json...")
        colleges = load_json_as_list("college_details.json")
        imported_before = total_imported
        for col in colleges:
            if not isinstance(col, dict):
                continue
            name = safe_str(col.get("name", ""))
            if not name:
                continue
            existing = db.query(School).filter(School.name == name).first()
            if existing:
                total_skipped += 1
                continue
            slug = name.replace("大学", "").replace("学院", "").replace(" ", "")[:50]
            province = safe_str(col.get("province", ""))
            tags = col.get("tags", [])
            level = "985" if "985高校" in tags else ("211" if "211高校" in tags else ("双一流" if "双一流" in tags else "普通"))
            db.add(School(
                name=name[:100], slug=slug, province=province[:20] if province else None,
                level=level,
                ranking=col.get("ranking"),
                key_majors=col.get("departments"),
                employment_rate=col.get("employment_rate"),
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 14. major_crawled.json (837 majors) ===
        print("\n14. major_crawled.json...")
        major_data = load_json("major_crawled.json")
        imported_before = total_imported
        if isinstance(major_data, dict) and "majors" in major_data:
            for m in major_data["majors"]:
                if not isinstance(m, dict):
                    continue
                name = safe_str(m.get("name", ""))
                code = safe_str(m.get("code", ""))
                if not name:
                    continue
                title = f"{code} {name}" if code else name
                title = title[:200]
                existing = db.query(KnowledgeArticle).filter(
                    KnowledgeArticle.title == title
                ).first()
                if existing:
                    total_skipped += 1
                    continue
                major_type = safe_str(m.get("type", ""))
                content = f"专业代码: {code}\n专业名称: {name}\n学位类型: {major_type}\n来源: {m.get('source', 'kaoyan.com')}"
                db.add(KnowledgeArticle(
                    title=title, content=content[:3000],
                    category="考研专业", tags=[major_type, "专业目录"],
                    source="kaoyan.com",
                ))
                total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # =====================================================================
        # NEW: Round 5 + Fast scrape imports
        # =====================================================================

        # === 15. fast_bilibili.json (194 B站 videos) ===
        print("\n15. fast_bilibili.json...")
        fast_bili = load_json_as_list("fast_bilibili.json")
        imported_before = total_imported
        for vid in fast_bili:
            if not isinstance(vid, dict):
                continue
            title = safe_str(vid.get("title", ""))
            if not title:
                continue
            title = title[:200]
            existing = db.query(KnowledgeArticle).filter(KnowledgeArticle.title == title).first()
            if existing:
                total_skipped += 1
                continue
            desc = safe_str(vid.get("description", ""))
            url = safe_str(vid.get("url", ""))
            views = safe_int(vid.get("views", 0))
            author = safe_str(vid.get("author", ""))
            keyword = safe_str(vid.get("keyword", "考研"))
            content = f"视频标题: {title}\n作者: {author}\n播放量: {views}\n简介: {desc}\n链接: {url}"
            db.add(KnowledgeArticle(
                title=title, content=content[:3000], category="B站考研视频",
                tags=[keyword], source="bilibili.com",
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 16. fast_yz.json (50 研招网 articles with CSS/HTML) ===
        print("\n16. fast_yz.json...")
        fast_yz = load_json_as_list("fast_yz.json")
        imported_before = total_imported
        for item in fast_yz:
            if not isinstance(item, dict):
                continue
            url = safe_str(item.get("url", ""))
            raw_content = safe_str(item.get("content", ""))
            if not raw_content or len(raw_content) < 50:
                continue
            clean = strip_css_js(raw_content)
            if len(clean) < 30:
                continue
            title = clean.split('.')[0].split(':')[0][:200] if clean else url[:200]
            existing = db.query(KnowledgeArticle).filter(KnowledgeArticle.title == title).first()
            if existing:
                total_skipped += 1
                continue
            db.add(KnowledgeArticle(
                title=title, content=clean[:3000],
                category="研招网资讯", tags=["研招网"],
                source="yz.chsi.com.cn",
            ))
            total_imported += 1
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 17. fast_colleges.json (SKIP: raw page templates, no usable college data) ===
        print("\n17. fast_colleges.json... (skipped - raw HTML templates, no college names)")

        # === 18. round5_kaoyan.json (10 考研经验) ===
        print("\n18. round5_kaoyan.json...")
        r5_kaoyan = load_json_as_list("round5_kaoyan.json")
        imported_before = total_imported
        for art in r5_kaoyan:
            if not isinstance(art, dict):
                continue
            title = safe_str(art.get("title", ""))
            if not title:
                continue
            title = title[:200]
            existing = db.query(ExperiencePost).filter(ExperiencePost.title == title).first()
            if existing:
                total_skipped += 1
                continue
            content = safe_str(art.get("content", ""))
            category = safe_str(art.get("category", "experience"))
            url = safe_str(art.get("url", ""))
            try:
                db.add(ExperiencePost(
                    title=title, content=content[:3000], summary=content[:200],
                    tags=["考研"], category=category,
                    user_id=user.id, source_platform="crawler",
                    source_url=url,
                    view_count=300, like_count=20,
                ))
                db.flush()
                total_imported += 1
            except Exception as e:
                db.rollback()
                total_skipped += 1
                print(f"  SKIP: {title[:50]}... - {e}")
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 19. round5_bilibili.json (8 B站 videos) ===
        print("\n19. round5_bilibili.json...")
        r5_bili = load_json_as_list("round5_bilibili.json")
        imported_before = total_imported
        for vid in r5_bili:
            if not isinstance(vid, dict):
                continue
            title = safe_str(vid.get("title", ""))
            if not title:
                continue
            title = title[:200]
            existing = db.query(KnowledgeArticle).filter(KnowledgeArticle.title == title).first()
            if existing:
                total_skipped += 1
                continue
            desc = safe_str(vid.get("description", ""))
            url = safe_str(vid.get("url", ""))
            views = safe_int(vid.get("views", 0))
            author = safe_str(vid.get("author", ""))
            keyword = safe_str(vid.get("keyword", "考研"))
            content = f"视频标题: {title}\n作者: {author}\n播放量: {views}\n简介: {desc}\n链接: {url}"
            try:
                db.add(KnowledgeArticle(
                    title=title, content=content[:3000], category="B站考研视频",
                    tags=[keyword], source="bilibili.com",
                ))
                db.flush()
                total_imported += 1
            except Exception as e:
                db.rollback()
                total_skipped += 1
                print(f"  SKIP: {title[:50]}... - {e}")
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 20. round5_yz.json (调剂/复试 sections) ===
        print("\n20. round5_yz.json...")
        r5_yz = load_json("round5_yz.json")
        imported_before = total_imported
        if isinstance(r5_yz, dict):
            for section_name, section_data in r5_yz.get("sections", {}).items():
                if not isinstance(section_data, dict):
                    continue
                pages = section_data.get("pages", [])
                for page in pages:
                    if not isinstance(page, dict):
                        continue
                    content = safe_str(page.get("markdown", "")) or safe_str(page.get("content", ""))
                    if not content or len(content) < 30:
                        continue
                    url = safe_str(page.get("url", ""))
                    title = safe_str(page.get("title", "")) or url[:200] or content[:200]
                    title = title[:200]
                    existing = db.query(KnowledgeArticle).filter(
                        KnowledgeArticle.title == title
                    ).first()
                    if existing:
                        total_skipped += 1
                        continue
                    try:
                        db.add(KnowledgeArticle(
                            title=title, content=content[:3000],
                            category="研招网资讯", tags=[section_name],
                            source="yz.chsi.com.cn",
                        ))
                        db.flush()
                        total_imported += 1
                    except Exception as e:
                        db.rollback()
                        total_skipped += 1
                        print(f"  SKIP: {title[:50]}... - {e}")
        db.commit()
        print(f"  New: {total_imported - imported_before}")

        # === 21. round5_colleges.json (5 colleges) ===
        print("\n21. round5_colleges.json...")
        r5_colleges = load_json_as_list("round5_colleges.json")
        imported_before = total_imported
        for col in r5_colleges:
            if not isinstance(col, dict):
                continue
            name = safe_str(col.get("name", ""))
            if not name:
                continue
            existing = db.query(School).filter(School.name == name).first()
            if existing:
                total_skipped += 1
                continue
            slug = name.replace("大学", "").replace("学院", "").replace(" ", "")[:50]
            province = safe_str(col.get("province", ""))
            tags = col.get("tags", [])
            level = "985" if "985高校" in tags else ("211" if "211高校" in tags else ("双一流" if "双一流" in tags else "普通"))
            try:
                db.add(School(
                    name=name[:100], slug=slug, province=province[:20] if province else None,
                    level=level,
                    key_majors=col.get("departments"),
                ))
                db.flush()
                total_imported += 1
            except Exception as e:
                db.rollback()
                total_skipped += 1
                print(f"  SKIP: {name} - {e}")
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

        try:
            r = db.execute(text("SELECT COUNT(*) FROM experience_posts WHERE source_platform='crawler'"))
            print(f"\n  爬取经验帖: {r.scalar()}")
        except:
            pass

        try:
            r = db.execute(text("SELECT COUNT(*) FROM knowledge_articles WHERE source IS NOT NULL AND source != ''"))
            print(f"  爬取知识文章: {r.scalar()}")
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
