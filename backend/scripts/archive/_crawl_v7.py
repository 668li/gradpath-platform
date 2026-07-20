#!/usr/bin/env python3
"""GradPath 综合爬取引擎 v7 — 三域分离 + 新数据源"""
import httpx
import json
import time
import psycopg2
import re
import uuid
import asyncio
from datetime import datetime
from html import unescape
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

DB_URL = "postgresql://gradpath:changeme@db:5432/gradpath"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def get_db(): return psycopg2.connect(DB_URL)
def clean(t):
    if not t: return ""
    t = re.sub(r'<[^>]+>', '', str(t))
    return re.sub(r'\s+', ' ', unescape(t)).strip()[:5000]
def new_id(): return str(uuid.uuid4())

# ========== 考研数据源 ==========
GRAD_SOURCES = {
    "yanzhao": ("研招网", "https://yz.chsi.com.cn/kyzx/kydt/"),
    "kaoyan": ("考研帮", "https://www.kaoyan.com/experience/"),
    "eol_kaoyan": ("EOL考研", "https://kaoyan.eol.cn/"),
}

# ========== 考公数据源 ==========
CIVIL_SOURCES = {
    "offcn": ("中公教育", "https://www.offcn.com/gwy/"),
    "huatu": ("华图教育", "https://www.huatu.com/guojia/"),
    "hqwx": ("环球网校", "https://www.hqwx.com/gjgwy-kaoshi/"),
}

# ========== 就业数据源 ==========
CAREER_SOURCES = {
    "51job": ("前程无忧", "https://www.51job.com/"),
    "lagou": ("拉勾网", "https://www.lagou.com/"),
    "zhipin": ("BOSS直聘", "https://www.zhipin.com/"),
}

# ========== 新闻/教育数据源 ==========
NEWS_SOURCES = {
    "sina_edu": ("新浪教育", "https://edu.sina.com.cn/"),
    "xinhua_edu": ("新华网教育", "http://www.xinhuanet.com/edu/"),
    "163_edu": ("网易教育", "https://edu.163.com/"),
    "eol": ("中国教育在线", "https://www.eol.cn/kaoyan/"),
}

def crawl_page(url, timeout=10):
    """爬取单个页面"""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as c:
            r = c.get(url, headers=HEADERS)
            return r.text if r.status_code == 200 else None
    except:
        return None

def extract_articles(html, base_url):
    """从HTML提取文章链接"""
    if not html: return []
    soup = BeautifulSoup(html, 'lxml')
    articles = []
    seen = set()
    
    for a in soup.select('a[href]'):
        text = clean(a.get_text())
        href = a.get("href", "")
        if len(text) < 8 or text in seen: continue
        if not href.startswith("http"): 
            href = base_url.rstrip('/') + '/' + href.lstrip('/')
        seen.add(text)
        articles.append({"title": text, "url": href})
    
    return articles[:30]

# ========== 考研爬取 ==========
def crawl_grad(conn):
    print("\n[考研] 数据爬取")
    cur = conn.cursor()
    total = 0
    
    for key, (name, url) in GRAD_SOURCES.items():
        try:
            html = crawl_page(url)
            if not html:
                print(f"  [{name}] 无法访问")
                continue
            
            articles = extract_articles(html, url)
            count = 0
            for art in articles[:20]:
                title = art["title"]
                content = f"【{name}】{title}\n来源: {name}\n链接: {art['url']}"
                cur.execute(
                    "INSERT INTO knowledge_articles (id, title, content, source, category, tags, metadata, is_published, created_at) SELECT %s, %s, %s, %s, '考研', %s, '{}'::jsonb, true, NOW() WHERE NOT EXISTS (SELECT 1 FROM knowledge_articles WHERE title=%s)",
                    (new_id(), title, content, key, json.dumps([name, "考研"]), title)
                )
                count += cur.rowcount
            conn.commit()
            total += count
            print(f"  [{name}] +{count}条")
            time.sleep(1)
        except Exception as e:
            print(f"  [{name}] 错误: {str(e)[:60]}")
            conn.rollback()
    
    cur.close()
    return total

# ========== 考公爬取 → civil_service_post_intel ==========
def crawl_civil(conn):
    print("\n[考公] 数据爬取")
    cur = conn.cursor()
    total = 0
    uid = None
    cur.execute("SELECT id FROM users LIMIT 1")
    row = cur.fetchone()
    if row: uid = row[0]
    
    for key, (name, url) in CIVIL_SOURCES.items():
        try:
            html = crawl_page(url)
            if not html:
                print(f"  [{name}] 无法访问")
                continue
            
            soup = BeautifulSoup(html, 'lxml')
            articles = []
            for a in soup.select('a[href]'):
                text = clean(a.get_text())
                href = a.get("href", "")
                if len(text) < 8: continue
                if not any(kw in text for kw in ["国考", "省考", "公务员", "行测", "申论", "面试", "招录", "事业单位"]): continue
                if not href.startswith("http"): href = url.rstrip('/') + '/' + href.lstrip('/')
                articles.append({"title": text, "url": href})
            
            count = 0
            for art in articles[:20]:
                title = art["title"]
                cur.execute(
                    "INSERT INTO civil_service_post_intel (id, post_name, department, region, exam_type, work_content, data_sources, tags, created_at, user_id) SELECT %s, %s, '待查', '全国', '国考', %s, %s, %s, NOW(), %s WHERE NOT EXISTS (SELECT 1 FROM civil_service_post_intel WHERE post_name=%s)",
                    (new_id(), title, f"来源: {name}\n链接: {art['url']}", json.dumps([name]), json.dumps(["考公"]), uid, title)
                )
                count += cur.rowcount
            conn.commit()
            total += count
            print(f"  [{name}] +{count}条")
            time.sleep(1)
        except Exception as e:
            print(f"  [{name}] 错误: {str(e)[:60]}")
            conn.rollback()
    
    cur.close()
    return total

# ========== 就业爬取 → experience_posts + market_data ==========
def crawl_career(conn):
    print("\n[就业] 数据爬取")
    cur = conn.cursor()
    total = 0
    
    for key, (name, url) in CAREER_SOURCES.items():
        try:
            html = crawl_page(url)
            if not html:
                print(f"  [{name}] 无法访问")
                continue
            
            soup = BeautifulSoup(html, 'lxml')
            articles = []
            for a in soup.select('a[href]'):
                text = clean(a.get_text())
                href = a.get("href", "")
                if len(text) < 8: continue
                if not any(kw in text for kw in ["招聘", "职位", "薪资", "面试", "求职", "offer", "简历", "工作"]): continue
                if not href.startswith("http"): href = url.rstrip('/') + '/' + href.lstrip('/')
                articles.append({"title": text, "url": href})
            
            count = 0
            for art in articles[:15]:
                title = art["title"]
                content = f"【{name}】{title}\n来源: {name}\n链接: {art['url']}"
                cur.execute(
                    "INSERT INTO experience_posts (id, user_id, title, summary, content, category, is_anonymous, status, view_count, like_count, comment_count, tags, source_platform, created_at) SELECT %s, %s, %s, %s, %s, 'career', true, 'approved', 0, 0, 0, %s, %s, NOW() WHERE NOT EXISTS (SELECT 1 FROM experience_posts WHERE title=%s)",
                    (new_id(), None, title[:100], title[:200], content, json.dumps([name, "就业"]), key, title[:100])
                )
                count += cur.rowcount
            conn.commit()
            total += count
            print(f"  [{name}] +{count}条")
            time.sleep(1)
        except Exception as e:
            print(f"  [{name}] 错误: {str(e)[:60]}")
            conn.rollback()
    
    cur.close()
    return total

# ========== 新闻爬取 → knowledge_articles ==========
def crawl_news(conn):
    print("\n[新闻] 数据爬取")
    cur = conn.cursor()
    total = 0
    
    for key, (name, url) in NEWS_SOURCES.items():
        try:
            html = crawl_page(url)
            if not html:
                print(f"  [{name}] 无法访问")
                continue
            
            articles = extract_articles(html, url)
            count = 0
            for art in articles[:20]:
                title = art["title"]
                content = f"【{name}】{title}\n来源: {name}\n链接: {art['url']}"
                cur.execute(
                    "INSERT INTO knowledge_articles (id, title, content, source, category, tags, metadata, is_published, created_at) SELECT %s, %s, %s, %s, '新闻', %s, '{}'::jsonb, true, NOW() WHERE NOT EXISTS (SELECT 1 FROM knowledge_articles WHERE title=%s)",
                    (new_id(), title, content, key, json.dumps([name, "新闻"]), title)
                )
                count += cur.rowcount
            conn.commit()
            total += count
            print(f"  [{name}] +{count}条")
            time.sleep(1)
        except Exception as e:
            print(f"  [{name}] 错误: {str(e)[:60]}")
            conn.rollback()
    
    cur.close()
    return total

if __name__ == "__main__":
    print(f"GradPath 综合爬取引擎 v7 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    conn = get_db()
    results = {}
    results["考研"] = crawl_grad(conn)
    results["考公"] = crawl_civil(conn)
    results["就业"] = crawl_career(conn)
    results["新闻"] = crawl_news(conn)
    conn.close()
    
    print("\n" + "=" * 60)
    total = sum(results.values())
    for domain, count in results.items():
        print(f"  {domain}: +{count}条")
    print(f"  总计: +{total}条")
