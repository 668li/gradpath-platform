"""统一导入脚本 — 将爬取的JSON数据批量导入GradPath数据库。

使用SQL批量插入提高速度，去重检查防止重复导入。
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# 确保 app 包可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.database import SessionLocal, engine
from app.models import ExperiencePost, KnowledgeArticle, School, KaoyanNews

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def clean_content(raw: str) -> str:
    """清理爬取内容中的CSS、HTML标签和多余空白。"""
    # 去除嵌入的CSS块 (/* tailwindcss ... */ 及 @layer 块)
    text = re.sub(r'/\*!?\s*tailwindcss[^*]*\*/', '', raw)
    text = re.sub(r'/\*[^*]*\*/', '', text)
    text = re.sub(r'@layer[^{]*\{[^}]*\}', '', text)
    # 去除 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', text)
    # 去除 CSS 属性声明
    text = re.sub(r'[\w-]+\s*:\s*[^;{}]+;', '', text)
    # 去除 @media / @keyframes 等
    text = re.sub(r'@media[^{]*\{[^@]*\}', '', text)
    text = re.sub(r'@keyframes[^{]*\{[^}]*\}', '', text)
    # 合并多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_title_from_content(content: str, url: str = "") -> str:
    """从内容中提取有意义的标题。"""
    # 尝试匹配常见的文章标题模式
    # 模式1: "标题 发布于" 或 "标题 考研帮"
    patterns = [
        r'考研网（kaoyan.com）\s+(.{5,80}?)(?:\s+考研帮|\s+考研网|\s+发布于)',
        r'考研网（kaoyan.com）\s+(.{5,80}?)(?:\s+PART)',
        r'中财大MEM|研究生毕业|2026年|2027|海南|升学无忧|宁诺|澳门|欢迎报考|《2026|温肯|硬科技',
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            title = m.group(0) if m.lastindex is None else m.group(1)
            title = re.sub(r'\s+', ' ', title).strip()
            if len(title) > 200:
                title = title[:200]
            return title

    # 从URL提取
    if "uuid=" in url:
        return f"考研经验分享"
    if "chsi.com.cn" in url:
        parts = url.split("/")
        if len(parts) > 5:
            return parts[-1].replace(".html", "")

    return "考研资讯"


def classify_kaoyan_article(title: str, content: str) -> str:
    """根据内容分类考研经验贴。"""
    combined = (title + " " + content).lower()
    if any(k in combined for k in ["复试", "调剂", "面试"]):
        return "复试"
    if any(k in combined for k in ["择校", "院校", "学校", "选学校"]):
        return "择校"
    if any(k in combined for k in ["初试", "冲刺", "背诵", "复习", "备考"]):
        return "初试"
    if any(k in combined for k in ["大纲", "真题", "分数", "国家线"]):
        return "初试"
    return "general"


def classify_yz_article(title: str, content: str) -> str:
    """分类研招网文章。"""
    combined = (title + " " + content).lower()
    if any(k in combined for k in ["政策", "规定", "管理规定", "招生简章"]):
        return "政策"
    if any(k in combined for k in ["调剂"]):
        return "调剂"
    if any(k in combined for k in ["复试"]):
        return "复试"
    if any(k in combined for k in ["招生", "报考", "报名"]):
        return "招生简章"
    return "general"


def extract_tags(content: str) -> list:
    """从内容中提取标签。"""
    tags = []
    tag_keywords = {
        "政治": "政治", "英语": "英语", "数学": "数学",
        "专业课": "专业课", "复试": "复试", "调剂": "调剂",
        "择校": "择校", "经验": "经验", "备考": "备考",
        "背诵": "背诵", "冲刺": "冲刺", "大纲": "大纲",
        "真题": "真题", "作文": "作文", "阅读": "阅读",
        "奖学金": "奖学金", "资助": "资助", "招生": "招生",
    }
    for kw, tag in tag_keywords.items():
        if kw in content:
            tags.append(tag)
    return tags[:5]


def import_fast_kaoyan(db, system_user_id):
    """导入 fast_kaoyan.json → experience_posts。"""
    path = os.path.join(DATA_DIR, "fast_kaoyan.json")
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        print("[SKIP] fast_kaoyan.json is empty")
        return 0

    # 获取已有URL去重
    existing_urls = set(
        row[0] for row in db.query(ExperiencePost.source_url)
        .filter(ExperiencePost.source_url.isnot(None))
        .all()
    )

    count = 0
    for item in items:
        url = item.get("url", "")
        if url in existing_urls:
            continue

        raw_content = item.get("content", "")
        clean = clean_content(raw_content)
        title = extract_title_from_content(raw_content, url)
        category = classify_kaoyan_article(title, raw_content)
        tags = extract_tags(raw_content)

        post = ExperiencePost(
            user_id=system_user_id,
            title=title[:200],
            summary=clean[:500] if len(clean) > 500 else clean,
            content=clean,
            tags=tags,
            category=category,
            source_platform="crawler",
            source_url=url,
            status="approved",
            is_verified=True,
        )
        db.add(post)
        count += 1

    db.commit()
    return count


def import_fast_yz(db):
    """导入 fast_yz.json → knowledge_articles。"""
    path = os.path.join(DATA_DIR, "fast_yz.json")
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        print("[SKIP] fast_yz.json is empty")
        return 0

    # 获取已有URL去重
    existing_urls = set()
    rows = db.execute(text("SELECT metadata->>'url' FROM knowledge_articles WHERE metadata->>'url' IS NOT NULL")).fetchall()
    existing_urls = set(row[0] for row in rows if row[0])

    count = 0
    for item in items:
        url = item.get("url", "")
        if url in existing_urls:
            continue

        raw_content = item.get("content", "")
        clean = clean_content(raw_content)
        title = extract_title_from_content(raw_content, url)
        category = classify_yz_article(title, raw_content)
        tags = extract_tags(raw_content)

        article = KnowledgeArticle(
            category=category,
            title=title[:200],
            content=clean,
            tags=tags,
            source="yz.chsi.com.cn",
            metadata_={"url": url, "source_platform": "crawler"},
            is_published=True,
        )
        db.add(article)
        count += 1

    db.commit()
    return count


def import_bilibili_loop(db):
    """导入 bilibili_loop.json → knowledge_articles (B站视频)。"""
    path = os.path.join(DATA_DIR, "bilibili_loop.json")
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        print("[SKIP] bilibili_loop.json is empty")
        return 0

    # 获取已有URL去重
    existing_urls = set()
    rows = db.execute(text("SELECT metadata->>'url' FROM knowledge_articles WHERE metadata->>'url' IS NOT NULL")).fetchall()
    existing_urls = set(row[0] for row in rows if row[0])

    count = 0
    for item in items:
        url = item.get("url", "")
        if url in existing_urls:
            continue

        title = item.get("title", "")[:200]
        description = item.get("description", "")
        author = item.get("author", "")
        keyword = item.get("keyword", "")

        article = KnowledgeArticle(
            category="skill_map",
            title=title,
            content=description or title,
            tags=["B站", "视频", keyword] if keyword else ["B站", "视频"],
            source="bilibili",
            metadata_={
                "url": url,
                "author": author,
                "views": item.get("views", 0),
                "keyword": keyword,
                "source_platform": "crawler",
            },
            is_published=True,
        )
        db.add(article)
        count += 1

    db.commit()
    return count


def import_college_loop(db):
    """导入 college_loop.json → knowledge_articles (院校信息)。

    内容为原始HTML，提取可用文本信息。
    """
    path = os.path.join(DATA_DIR, "college_loop.json")
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        print("[SKIP] college_loop.json is empty")
        return 0

    # 获取已有去重
    existing_ids = set(
        row[0] for row in db.execute(
            text("SELECT metadata->>'crawler_id' FROM knowledge_articles WHERE metadata->>'crawler_id' IS NOT NULL")
        ).fetchall()
    )

    count = 0
    for item in items:
        crawler_id = str(item.get("id", ""))
        if crawler_id in existing_ids:
            continue

        raw_content = item.get("content", "")
        clean = clean_content(raw_content)

        # 尝试从内容提取标题
        title_match = re.search(r'考研网（kaoyan.com）\s*(.{5,80}?)(?:\s+考研帮|\s+发布于)', raw_content)
        title = title_match.group(1).strip() if title_match else f"院校信息-{crawler_id}"

        article = KnowledgeArticle(
            category="education_path",
            title=title[:200],
            content=clean,
            tags=["院校信息", "kaoyan.com"],
            source="kaoyan.com",
            metadata_={"crawler_id": crawler_id, "source_platform": "crawler"},
            is_published=True,
        )
        db.add(article)
        count += 1

        if count % 100 == 0:
            db.commit()
            print(f"  ... 已导入 {count} 条院校信息")

    db.commit()
    return count


def import_firecrawl_loop(db):
    """导入 firecrawl_loop.json → knowledge_articles (Firecrawl爬取的考研网内容)。"""
    path = os.path.join(DATA_DIR, "firecrawl_loop.json")
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("articles", [])
    if not items:
        print("[SKIP] firecrawl_loop.json has no articles")
        return 0

    # 获取已有URL去重
    existing_urls = set()
    rows = db.execute(text("SELECT metadata->>'url' FROM knowledge_articles WHERE metadata->>'url' IS NOT NULL")).fetchall()
    existing_urls = set(row[0] for row in rows if row[0])

    count = 0
    for item in items:
        url = item.get("url", "")
        if url in existing_urls:
            continue

        raw_content = item.get("content", "")
        clean = clean_content(raw_content)
        title = item.get("title", "")[:200] or extract_title_from_content(raw_content, url)
        category = item.get("category", classify_kaoyan_article(title, raw_content))
        section = item.get("section", "")
        source = item.get("source", "kaoyan.com")
        tags = extract_tags(raw_content)

        article = KnowledgeArticle(
            category=category,
            title=title[:200],
            content=clean,
            tags=tags + [section] if section else tags,
            source=source,
            metadata_={"url": url, "section": section, "source_platform": "crawler"},
            is_published=True,
        )
        db.add(article)
        count += 1

    db.commit()
    return count


def import_yz_loop(db):
    """导入 yz_loop.json → knowledge_articles (研招网各栏目文章)。

    数据结构: {sections: {kydt: {items: [...]}, jybzc: {...}, ...}}
    注意: 这些条目通常只有标题和URL，没有正文内容。
    """
    path = os.path.join(DATA_DIR, "yz_loop.json")
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = data.get("sections", {})
    if not sections:
        print("[SKIP] yz_loop.json has no sections")
        return 0

    # 获取已有URL去重
    existing_urls = set()
    rows = db.execute(text("SELECT metadata->>'url' FROM knowledge_articles WHERE metadata->>'url' IS NOT NULL")).fetchall()
    existing_urls = set(row[0] for row in rows if row[0])

    section_name_map = {
        "kydt": "考研动态",
        "jybzc": "就业政策",
        "zsjz": "招生简章",
        "fstj": "复试调剂",
    }

    count = 0
    for section_key, section_data in sections.items():
        items = section_data.get("items", [])
        section_name = section_name_map.get(section_key, section_key)

        for item in items:
            url = item.get("url", "")
            if url in existing_urls:
                continue

            title = item.get("title", "")[:200]
            date = item.get("date", "")
            source = item.get("source", "yz.chsi.com.cn")

            article = KnowledgeArticle(
                category=classify_yz_article(title, ""),
                title=title,
                content=f"{title}\n来源: {source}\n日期: {date}" if date else title,
                tags=["研招网", section_name],
                source=source,
                metadata_={
                    "url": url,
                    "date": date,
                    "section": section_name,
                    "source_platform": "crawler",
                },
                is_published=True,
            )
            db.add(article)
            count += 1

    db.commit()
    return count


def import_sina_koolearn(db):
    """导入 sina_koolearn.json → knowledge_articles (新浪/新东方考研内容)。"""
    path = os.path.join(DATA_DIR, "sina_koolearn.json")
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        print("[SKIP] sina_koolearn.json is empty")
        return 0

    # 获取已有URL去重
    existing_urls = set()
    rows = db.execute(text("SELECT metadata->>'url' FROM knowledge_articles WHERE metadata->>'url' IS NOT NULL")).fetchall()
    existing_urls = set(row[0] for row in rows if row[0])

    count = 0
    for item in items:
        url = item.get("url", "")
        if url in existing_urls:
            continue

        source_name = item.get("source", "新浪考研")
        raw_content = item.get("content", "")
        clean = clean_content(raw_content)
        title = extract_title_from_content(raw_content, url)
        tags = extract_tags(raw_content)

        article = KnowledgeArticle(
            category="general",
            title=title[:200],
            content=clean,
            tags=tags + [source_name],
            source=source_name,
            metadata_={"url": url, "source_platform": "crawler"},
            is_published=True,
        )
        db.add(article)
        count += 1

    db.commit()
    return count


def import_webfetch_articles(db):
    """导入 webfetch_articles.json → knowledge_articles (Firecrawl抓取的文章HTML)。"""
    path = os.path.join(DATA_DIR, "webfetch_articles.json")
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found")
        return 0

    with open(path, "r", encoding="utf-8-sig") as f:
        items = json.load(f)

    if not items:
        print("[SKIP] webfetch_articles.json is empty")
        return 0

    # 获取已有URL去重
    existing_urls = set()
    rows = db.execute(text("SELECT metadata->>'url' FROM knowledge_articles WHERE metadata->>'url' IS NOT NULL")).fetchall()
    existing_urls = set(row[0] for row in rows if row[0])

    count = 0
    for item in items:
        url = item.get("url", "")
        if url in existing_urls:
            continue

        raw_content = item.get("content", "")
        clean = clean_content(raw_content)
        title = extract_title_from_content(raw_content, url)
        tags = extract_tags(raw_content)

        article = KnowledgeArticle(
            category=classify_kaoyan_article(title, raw_content),
            title=title[:200],
            content=clean,
            tags=tags,
            source="kaoyan.com",
            metadata_={"url": url, "chars": item.get("chars", 0), "source_platform": "crawler"},
            is_published=True,
        )
        db.add(article)
        count += 1

    db.commit()
    return count


def verify_counts(db):
    """验证各表数据量。"""
    results = {}
    for model, name in [
        (ExperiencePost, "experience_posts"),
        (KnowledgeArticle, "knowledge_articles"),
        (School, "schools"),
        (KaoyanNews, "kaoyan_news"),
    ]:
        count = db.query(model).count()
        results[name] = count
    return results


def main():
    print("=" * 60)
    print("GradPath 统一数据导入脚本")
    print("=" * 60)

    db = SessionLocal()

    # 获取系统用户ID
    from app.models import User
    system_user = db.query(User).filter(User.name == "系统").first()
    if not system_user:
        print("[ERROR] 找不到系统用户，请先创建用户 '系统'")
        db.close()
        return
    system_user_id = system_user.id
    print(f"系统用户ID: {system_user_id}")

    # 导入前数据量
    print("\n--- 导入前数据量 ---")
    before = verify_counts(db)
    for name, count in before.items():
        print(f"  {name}: {count}")

    # 1. fast_kaoyan → experience_posts
    print("\n[1/7] 导入 fast_kaoyan.json → experience_posts ...")
    kaoyan_count = import_fast_kaoyan(db, system_user_id)
    print(f"  ✓ 导入 {kaoyan_count} 条经验贴")

    # 2. fast_yz → knowledge_articles
    print("\n[2/7] 导入 fast_yz.json → knowledge_articles ...")
    yz_count = import_fast_yz(db)
    print(f"  ✓ 导入 {yz_count} 条研招网文章")

    # 3. college_loop → knowledge_articles
    print("\n[3/7] 导入 college_loop.json → knowledge_articles (院校信息) ...")
    college_count = import_college_loop(db)
    print(f"  ✓ 导入 {college_count} 条院校信息")

    # 4. bilibili_loop → knowledge_articles
    print("\n[4/7] 导入 bilibili_loop.json → knowledge_articles (B站视频) ...")
    bilibili_count = import_bilibili_loop(db)
    print(f"  ✓ 导入 {bilibili_count} 条B站视频")

    # 5. firecrawl_loop → knowledge_articles
    print("\n[5/7] 导入 firecrawl_loop.json → knowledge_articles (Firecrawl) ...")
    firecrawl_count = import_firecrawl_loop(db)
    print(f"  ✓ 导入 {firecrawl_count} 条Firecrawl文章")

    # 6. yz_loop → knowledge_articles
    print("\n[6/7] 导入 yz_loop.json → knowledge_articles (研招网栏目) ...")
    yz_loop_count = import_yz_loop(db)
    print(f"  ✓ 导入 {yz_loop_count} 条研招网栏目文章")

    # 7. sina_koolearn → knowledge_articles
    print("\n[7a] 导入 sina_koolearn.json → knowledge_articles (新浪/新东方) ...")
    sina_count = import_sina_koolearn(db)
    print(f"  ✓ 导入 {sina_count} 条新浪/新东方文章")

    # 8. webfetch_articles → knowledge_articles
    print("\n[7b] 导入 webfetch_articles.json → knowledge_articles (Firecrawl文章) ...")
    webfetch_count = import_webfetch_articles(db)
    print(f"  ✓ 导入 {webfetch_count} 条Firecrawl文章")

    # 导入后数据量
    print("\n--- 导入后数据量 ---")
    after = verify_counts(db)
    for name, count in after.items():
        delta = count - before[name]
        print(f"  {name}: {count} (+{delta})")

    total_ka = yz_count + college_count + bilibili_count + firecrawl_count + yz_loop_count + sina_count + webfetch_count
    print("\n" + "=" * 60)
    print("导入完成!")
    print(f"  experience_posts 新增: {kaoyan_count}")
    print(f"  knowledge_articles 新增: {total_ka}")
    print(f"  DB 总数据量: {sum(after.values())}")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()
