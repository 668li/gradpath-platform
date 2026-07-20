#!/usr/bin/env python3
"""GradPath 综合爬取引擎 v8 — 修复约束"""
import httpx, json, time, psycopg2, re, uuid
from datetime import datetime
from html import unescape
from bs4 import BeautifulSoup

DB_URL = "postgresql://gradpath:changeme@db:5432/gradpath"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
def get_db(): return psycopg2.connect(DB_URL)
def clean(t):
    if not t: return ""
    t = re.sub(r'<[^>]+>', '', str(t))
    return re.sub(r'\s+', ' ', unescape(t)).strip()[:5000]
def new_id(): return str(uuid.uuid4())

# 数据源配置
GRAD_SOURCES = [("研招网","https://yz.chsi.com.cn/kyzx/kydt/"),("考研帮","https://www.kaoyan.com/experience/"),("EOL考研","https://kaoyan.eol.cn/")]
CIVIL_SOURCES = [("中公教育","https://www.offcn.com/gwy/"),("华图教育","https://www.huatu.com/guojia/"),("环球网校","https://www.hqwx.com/gjgwy-kaoshi/")]
CAREER_SOURCES = [("前程无忧","https://www.51job.com/"),("BOSS直聘","https://www.zhipin.com/")]
NEWS_SOURCES = [("新浪教育","https://edu.sina.com.cn/"),("新华网教育","http://www.xinhuanet.com/edu/"),("网易教育","https://edu.163.com/"),("中国教育在线","https://www.eol.cn/kaoyan/")]

def crawl_page(url):
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as c:
            r = c.get(url, headers=HEADERS)
            return r.text if r.status_code == 200 else None
    except: return None

def extract_articles(html, url):
    if not html: return []
    soup = BeautifulSoup(html, 'lxml')
    arts, seen = [], set()
    for a in soup.select('a[href]'):
        text = clean(a.get_text())
        href = a.get("href", "")
        if len(text) < 8 or text in seen: continue
        if not href.startswith("http"): href = url.rstrip('/') + '/' + href.lstrip('/')
        seen.add(text)
        arts.append({"title": text, "url": href})
    return arts[:30]

# ========== 考研 ==========
def crawl_grad(conn):
    print("\n[考研] 知识文章")
    cur = conn.cursor()
    total = 0
    for name, url in GRAD_SOURCES:
        html = crawl_page(url)
        if not html: print(f"  [{name}] 无法访问"); continue
        arts = extract_articles(html, url)
        count = 0
        for art in arts[:20]:
            cur.execute(
                "INSERT INTO knowledge_articles (id, title, content, source, category, tags, metadata, is_published, created_at) SELECT %s, %s, %s, %s, '考研', %s, '{}'::jsonb, true, NOW() WHERE NOT EXISTS (SELECT 1 FROM knowledge_articles WHERE title=%s)",
                (new_id(), art["title"], f"【{name}】{art['title']}\n链接: {art['url']}", name.lower(), json.dumps([name]), art["title"])
            )
            count += cur.rowcount
        conn.commit()
        total += count
        print(f"  [{name}] +{count}条")
        time.sleep(1)
    cur.close()
    return total

# ========== 考公 → civil_service_post_intel (修复NOT NULL) ==========
def crawl_civil(conn):
    print("\n[考公] 职位情报")
    cur = conn.cursor()
    total = 0
    uid = None
    cur.execute("SELECT id FROM users LIMIT 1")
    r = cur.fetchone()
    if r: uid = r[0]
    
    for name, url in CIVIL_SOURCES:
        html = crawl_page(url)
        if not html: print(f"  [{name}] 无法访问"); continue
        soup = BeautifulSoup(html, 'lxml')
        arts = []
        for a in soup.select('a[href]'):
            text = clean(a.get_text())
            href = a.get("href", "")
            if len(text) < 8: continue
            if not any(kw in text for kw in ["国考","省考","公务员","行测","申论","面试","招录","事业单位"]): continue
            if not href.startswith("http"): href = url.rstrip('/') + '/' + href.lstrip('/')
            arts.append({"title": text, "url": href})
        
        count = 0
        for art in arts[:20]:
            try:
                cur.execute(
                    "INSERT INTO civil_service_post_intel (id, user_id, post_name, department, region, exam_type, real_competition, treatment_level, workload, data_sources, tags, work_content, created_at) VALUES (%s, %s, %s, '待查', '全国', '国考', 'unknown', 'unknown', 'unknown', %s, %s, %s, NOW())",
                    (new_id(), uid, art["title"], json.dumps([name]), json.dumps(["考公"]), f"来源: {name}\n{art['url']}")
                )
                count += cur.rowcount
            except: conn.rollback()
        conn.commit()
        total += count
        print(f"  [{name}] +{count}条")
        time.sleep(1)
    cur.close()
    return total

# ========== 就业 → experience_posts (修复user_id) ==========
def crawl_career(conn):
    print("\n[就业] 经验帖")
    cur = conn.cursor()
    total = 0
    uid = None
    cur.execute("SELECT id FROM users LIMIT 1")
    r = cur.fetchone()
    if r: uid = r[0]
    
    for name, url in CAREER_SOURCES:
        html = crawl_page(url)
        if not html: print(f"  [{name}] 无法访问"); continue
        soup = BeautifulSoup(html, 'lxml')
        arts = []
        for a in soup.select('a[href]'):
            text = clean(a.get_text())
            href = a.get("href", "")
            if len(text) < 8: continue
            if not any(kw in text for kw in ["招聘","职位","薪资","面试","求职","offer","简历","工作"]): continue
            if not href.startswith("http"): href = url.rstrip('/') + '/' + href.lstrip('/')
            arts.append({"title": text, "url": href})
        
        count = 0
        for art in arts[:15]:
            try:
                cur.execute(
                    "INSERT INTO experience_posts (id, user_id, title, summary, content, category, is_anonymous, status, view_count, like_count, comment_count, tags, source_platform, created_at) VALUES (%s, %s, %s, %s, %s, 'career', true, 'approved', 0, 0, 0, %s, %s, NOW())",
                    (new_id(), uid, art["title"][:100], art["title"][:200], f"【{name}】{art['title']}\n{art['url']}", json.dumps([name, "就业"]), name.lower())
                )
                count += cur.rowcount
            except: conn.rollback()
        conn.commit()
        total += count
        print(f"  [{name}] +{count}条")
        time.sleep(1)
    cur.close()
    return total

# ========== 新闻 → knowledge_articles ==========
def crawl_news(conn):
    print("\n[新闻] 知识库")
    cur = conn.cursor()
    total = 0
    for name, url in NEWS_SOURCES:
        html = crawl_page(url)
        if not html: print(f"  [{name}] 无法访问"); continue
        arts = extract_articles(html, url)
        count = 0
        for art in arts[:20]:
            cur.execute(
                "INSERT INTO knowledge_articles (id, title, content, source, category, tags, metadata, is_published, created_at) SELECT %s, %s, %s, %s, '新闻', %s, '{}'::jsonb, true, NOW() WHERE NOT EXISTS (SELECT 1 FROM knowledge_articles WHERE title=%s)",
                (new_id(), art["title"], f"【{name}】{art['title']}\n{art['url']}", name.lower(), json.dumps([name]), art["title"])
            )
            count += cur.rowcount
        conn.commit()
        total += count
        print(f"  [{name}] +{count}条")
        time.sleep(1)
    cur.close()
    return total

if __name__ == "__main__":
    print(f"GradPath 综合爬取 v8 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    conn = get_db()
    r = {}
    r["考研"] = crawl_grad(conn)
    r["考公"] = crawl_civil(conn)
    r["就业"] = crawl_career(conn)
    r["新闻"] = crawl_news(conn)
    conn.close()
    print("\n" + "=" * 60)
    for d, c in r.items(): print(f"  {d}: +{c}条")
    print(f"  总计: +{sum(r.values())}条")
