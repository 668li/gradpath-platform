#!/usr/bin/env python3
"""GradPath 综合爬虫 v2 — 批量爬取可达数据源"""
import httpx
import json
import time
import psycopg2
import re
from datetime import datetime
from html import unescape

DB_URL = "postgresql://gradpath:changeme@db:5432/gradpath"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def get_db():
    return psycopg2.connect(DB_URL)

def clean(text):
    if not text: return ""
    text = re.sub(r'<[^>]+>', '', str(text))
    text = unescape(text)
    return re.sub(r'\s+', ' ', text).strip()[:5000]

def get_system_user(cur):
    cur.execute("SELECT id FROM users LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else None

# ========== 1. B站视频 → knowledge_articles ==========
def crawl_bilibili(conn, user_id):
    print("\n[1/6] B站视频爬取")
    cur = conn.cursor()
    total = 0
    keywords = ["考研经验", "考研备考", "国考", "省考", "考公", "求职面试", "秋招", "春招"]
    
    for kw in keywords:
        try:
            url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&page=1"
            with httpx.Client(timeout=15) as c:
                r = c.get(url, headers=HEADERS)
                results = r.json().get("data", {}).get("result", []) or []
            
            for v in results[:25]:
                title = clean(v.get("title", ""))
                desc = clean(v.get("description", ""))
                author = v.get("author", "")
                bvid = v.get("bvid", "")
                play = v.get("play", 0)
                content = f"【{kw}】{desc}\n\nUP主: {author} | 播放: {play}\nhttps://www.bilibili.com/video/{bvid}"
                cur.execute(
                    "INSERT INTO knowledge_articles (title, content, source, category, is_published, created_at) SELECT %s, %s, 'bilibili', %s, true, NOW() WHERE NOT EXISTS (SELECT 1 FROM knowledge_articles WHERE title=%s)",
                    (title, content, kw, title)
                )
                total += cur.rowcount
            conn.commit()
            print(f"  [{kw}] {len(results)}条 → 导入{total}条")
            time.sleep(1)
        except Exception as e:
            print(f"  [{kw}] 错误: {str(e)[:60]}")
            conn.rollback()
    
    cur.close()
    return total

# ========== 2. GitHub资料 → knowledge_articles ==========
def crawl_github(conn, user_id):
    print("\n[2/6] GitHub资料爬取")
    cur = conn.cursor()
    total = 0
    keywords = ["考研资料", "kaoyan", "考研真题", "考公", "civil-service-exam", "interview"]
    
    for kw in keywords:
        try:
            url = f"https://api.github.com/search/repositories?q={kw}&sort=stars&per_page=20"
            with httpx.Client(timeout=15) as c:
                r = c.get(url, headers={**HEADERS, "Accept": "application/vnd.github.v3+json"})
                repos = r.json().get("items", [])
            
            for repo in repos:
                name = repo.get("name", "")
                desc = repo.get("description", "") or ""
                html_url = repo.get("html_url", "")
                stars = repo.get("stargazers_count", 0)
                lang = repo.get("language", "") or ""
                content = f"{desc}\n\nStars: {stars} | Lang: {lang}\n{html_url}"
                cur.execute(
                    "INSERT INTO knowledge_articles (title, content, source, category, is_published, created_at) SELECT %s, %s, 'github', %s, true, NOW() WHERE NOT EXISTS (SELECT 1 FROM knowledge_articles WHERE title=%s)",
                    (name, content, kw, name)
                )
                total += cur.rowcount
            conn.commit()
            print(f"  [{kw}] {len(repos)}条 → 累计{total}条")
            time.sleep(1)
        except Exception as e:
            print(f"  [{kw}] 错误: {str(e)[:60]}")
            conn.rollback()
    
    cur.close()
    return total

# ========== 3. 华图教育考公 → civil_service_post_intel ==========
def crawl_huatu(conn, user_id):
    print("\n[3/6] 华图教育考公数据")
    cur = conn.cursor()
    total = 0
    
    try:
        url = "https://www.huatu.com/guojia/"
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            r = c.get(url, headers=HEADERS)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'lxml')
            
            links = soup.select('a[href]')
            seen = set()
            for link in links:
                text = clean(link.get_text())
                href = link.get("href", "")
                if not text or len(text) < 6 or text in seen:
                    continue
                if any(kw in text for kw in ["国考", "职位", "公告", "报名", "公务员", "行测", "申论"]):
                    seen.add(text)
                    cur.execute(
                        "INSERT INTO civil_service_post_intel (post_name, department, region, exam_type, work_content, data_sources, created_at, user_id) SELECT %s, '国家公务员', '全国', '国考', %s, %s, NOW(), %s WHERE NOT EXISTS (SELECT 1 FROM civil_service_post_intel WHERE post_name=%s)",
                        (text, f"来源: 华图教育\n链接: {href}", json.dumps(["华图教育"]), user_id, text)
                    )
                    total += cur.rowcount
            
            conn.commit()
            print(f"  华图考公: 提取{len(seen)}条 → 导入{total}条")
    except Exception as e:
        print(f"  华图错误: {str(e)[:80]}")
        conn.rollback()
    
    cur.close()
    return total

# ========== 4. 考研帮QA → qas ==========
def crawl_kaoyan_qa(conn, user_id):
    print("\n[4/6] 考研帮QA数据")
    cur = conn.cursor()
    total = 0
    
    try:
        url = "https://www.kaoyan.com/zhidao/"
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            r = c.get(url, headers=HEADERS)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'lxml')
            
            items = soup.select('a')
            seen = set()
            for item in items:
                text = clean(item.get_text())
                if not text or len(text) < 6 or text in seen:
                    continue
                if any(kw in text for kw in ["考研", "专业", "院校", "分数", "调剂", "复试", "初试"]):
                    seen.add(text)
                    cur.execute(
                        "INSERT INTO qas (user_id, title, content, status, view_count, answer_count, is_resolved, created_at) SELECT %s, %s, %s, 'active', 0, 0, false, NOW() WHERE NOT EXISTS (SELECT 1 FROM qas WHERE title=%s)",
                        (user_id, text, f"来源: 考研帮\nhttps://www.kaoyan.com/zhidao/", text)
                    )
                    total += cur.rowcount
            
            conn.commit()
            print(f"  考研帮QA: 提取{len(seen)}条 → 导入{total}条")
    except Exception as e:
        print(f"  考研帮错误: {str(e)[:80]}")
        conn.rollback()
    
    cur.close()
    return total

# ========== 5. 研招网调剂 → grad_adjustment_info ==========
def crawl_yz(conn, user_id):
    print("\n[5/6] 研招网调剂数据")
    cur = conn.cursor()
    total = 0
    
    try:
        url = "https://yz.chsi.com.cn/yztj/"
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            r = c.get(url, headers=HEADERS)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, 'lxml')
            
            items = soup.select('a')
            seen = set()
            for item in items:
                text = clean(item.get_text())
                href = item.get("href", "")
                if not text or len(text) < 6 or text in seen:
                    continue
                if any(kw in text for kw in ["大学", "学院", "调剂", "招生"]):
                    seen.add(text)
                    cur.execute(
                        "INSERT INTO grad_adjustment_info (university_name, major_name, source_url, year, status, created_at) SELECT %s, '待查', %s, 2026, 'active', NOW() WHERE NOT EXISTS (SELECT 1 FROM grad_adjustment_info WHERE university_name=%s)",
                        (text, href, text)
                    )
                    total += cur.rowcount
            
            conn.commit()
            print(f"  研招网: 提取{len(seen)}条 → 导入{total}条")
    except Exception as e:
        print(f"  研招网错误: {str(e)[:80]}")
        conn.rollback()
    
    cur.close()
    return total

# ========== 6. 微博搜索 → experience_posts ==========
def crawl_weibo(conn, user_id):
    print("\n[6/6] 微博考研/考公讨论")
    cur = conn.cursor()
    total = 0
    
    try:
        keywords = ["考研", "国考", "求职"]
        for kw in keywords:
            url = f"https://s.weibo.com/weibo?q={kw}"
            with httpx.Client(timeout=15, follow_redirects=True) as c:
                r = c.get(url, headers=HEADERS)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, 'lxml')
                
                posts = soup.select('.txt')
                for post in posts[:20]:
                    text = clean(post.get_text())
                    if len(text) < 10:
                        continue
                    cur.execute(
                        "INSERT INTO experience_posts (user_id, title, summary, content, category, is_anonymous, status, view_count, like_count, comment_count, tags, source_platform, created_at) SELECT %s, %s, %s, %s, 'general', true, 'approved', 0, 0, 0, %s, 'weibo', NOW() WHERE NOT EXISTS (SELECT 1 FROM experience_posts WHERE title=%s)",
                        (user_id, text[:100], text[:200], text, json.dumps([kw]), text[:100])
                    )
                    total += cur.rowcount
                conn.commit()
                print(f"  微博[{kw}]: 累计{total}条")
                time.sleep(1)
    except Exception as e:
        print(f"  微博错误: {str(e)[:80]}")
        conn.rollback()
    
    cur.close()
    return total

# ========== 主循环 ==========
if __name__ == "__main__":
    print(f"GradPath 综合爬虫 v2 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    conn = get_db()
    cur = conn.cursor()
    user_id = get_system_user(cur)
    cur.close()
    
    if not user_id:
        print("错误: 数据库中没有用户，无法插入需要user_id的表")
        exit(1)
    
    results = {}
    results["bilibili"] = crawl_bilibili(conn, user_id)
    results["github"] = crawl_github(conn, user_id)
    results["huatu"] = crawl_huatu(conn, user_id)
    results["kaoyan_qa"] = crawl_kaoyan_qa(conn, user_id)
    results["yz"] = crawl_yz(conn, user_id)
    results["weibo"] = crawl_weibo(conn, user_id)
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("爬取完成汇总:")
    total = 0
    for source, count in results.items():
        print(f"  {source}: {count} 条")
        total += count
    print(f"  总计新增: {total} 条")
    print(f"结束: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
