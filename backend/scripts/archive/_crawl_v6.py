#!/usr/bin/env python3
"""GradPath 综合爬虫 v6 — 最终可用版"""
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
def exists(cur, table, col, val):
    cur.execute(f"SELECT 1 FROM {table} WHERE {col}=%s LIMIT 1", (val,))
    return cur.fetchone() is not None

# ========== 1. B站视频 ==========
def crawl_bilibili(conn):
    print("\n[1/6] B站视频")
    cur = conn.cursor()
    total = 0
    # 获取cookie
    try:
        with httpx.Client(timeout=10) as c:
            c.get("https://www.bilibili.com/", headers=HEADERS)
            cookies = dict(c.cookies)
    except: cookies = {}
    
    keywords = ["考研经验", "考研备考", "国考", "省考", "考公", "求职面试"]
    for kw in keywords:
        try:
            url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&page=1"
            with httpx.Client(timeout=15, cookies=cookies) as c:
                r = c.get(url, headers=HEADERS)
                if r.status_code == 412:
                    print(f"  [{kw}] 被限流(412)，跳过")
                    time.sleep(3)
                    continue
                if r.status_code != 200:
                    print(f"  [{kw}] HTTP {r.status_code}")
                    continue
                data = r.json()
                results = data.get("data", {}).get("result") or []
            
            count = 0
            for v in results[:30]:
                title = clean(v.get("title", ""))
                desc = clean(v.get("description", ""))
                author = v.get("author", "")
                bvid = v.get("bvid", "")
                play = v.get("play", 0)
                content = f"【{kw}】{desc}\n\nUP主: {author} | 播放: {play}\nhttps://www.bilibili.com/video/{bvid}"
                if exists(cur, "knowledge_articles", "title", title):
                    continue
                cur.execute(
                    "INSERT INTO knowledge_articles (id, title, content, source, category, tags, metadata, is_published, created_at) VALUES (%s, %s, %s, 'bilibili', %s, %s::jsonb, '{}'::jsonb, true, NOW())",
                    (new_id(), title, content, kw, json.dumps([kw]))
                )
                count += 1
            conn.commit()
            total += count
            print(f"  [{kw}] {len(results)}条 → 新增{count}条")
            time.sleep(2)
        except Exception as e:
            print(f"  [{kw}] 错误: {str(e)[:60]}")
            conn.rollback()
    cur.close()
    return total

# ========== 2. GitHub资料 ==========
def crawl_github(conn):
    print("\n[2/6] GitHub资料")
    cur = conn.cursor()
    total = 0
    keywords = ["考研资料", "kaoyan", "考研真题", "考公", "interview-prep"]
    for kw in keywords:
        try:
            url = f"https://api.github.com/search/repositories?q={kw}&sort=stars&per_page=20"
            with httpx.Client(timeout=15) as c:
                r = c.get(url, headers={**HEADERS, "Accept": "application/vnd.github.v3+json"})
                repos = r.json().get("items", [])
            count = 0
            for repo in repos:
                name = repo.get("name", "")
                desc = repo.get("description", "") or ""
                html_url = repo.get("html_url", "")
                stars = repo.get("stargazers_count", 0)
                content = f"{desc}\n\nStars: {stars}\n{html_url}"
                if exists(cur, "knowledge_articles", "title", name):
                    continue
                cur.execute(
                    "INSERT INTO knowledge_articles (id, title, content, source, category, tags, metadata, is_published, created_at) VALUES (%s, %s, %s, 'github', %s, %s::jsonb, '{}'::jsonb, true, NOW())",
                    (new_id(), name, content, kw, json.dumps([kw, "github"]))
                )
                count += 1
            conn.commit()
            total += count
            print(f"  [{kw}] {len(repos)}条 → 新增{count}条")
            time.sleep(1)
        except Exception as e:
            print(f"  [{kw}] 错误: {str(e)[:60]}")
            conn.rollback()
    cur.close()
    return total

# ========== 3. 华图教育考公 ==========
def crawl_huatu(conn):
    print("\n[3/6] 华图教育考公")
    cur = conn.cursor()
    total = 0
    uid = None
    cur.execute("SELECT id FROM users LIMIT 1")
    r = cur.fetchone()
    if r: uid = r[0]
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            r = c.get("https://www.huatu.com/guojia/", headers=HEADERS)
            soup = BeautifulSoup(r.text, 'lxml')
            for tag in soup.select('li, h2, h3, a'):
                text = clean(tag.get_text())
                if len(text) < 8: continue
                if not any(kw in text for kw in ["国考", "职位", "公告", "公务员", "行测", "申论", "报名", "面试", "招录"]): continue
                if exists(cur, "civil_service_post_intel", "post_name", text):
                    continue
                cur.execute(
                    "INSERT INTO civil_service_post_intel (id, post_name, department, region, exam_type, work_content, data_sources, tags, created_at, user_id) VALUES (%s, %s, '国家公务员', '全国', '国考', %s, %s, %s, NOW(), %s)",
                    (new_id(), text, f"来源: 华图教育", json.dumps(["华图教育"]), json.dumps(["国考"]), uid)
                )
                total += cur.rowcount
            conn.commit()
            print(f"  华图: +{total}条")
    except Exception as e:
        print(f"  华图错误: {str(e)[:80]}")
        conn.rollback()
    cur.close()
    return total

# ========== 4. 考研帮QA ==========
def crawl_kaoyan(conn):
    print("\n[4/6] 考研帮")
    cur = conn.cursor()
    total = 0
    uid = None
    cur.execute("SELECT id FROM users LIMIT 1")
    r = cur.fetchone()
    if r: uid = r[0]
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            r = c.get("https://www.kaoyan.com/", headers=HEADERS)
            soup = BeautifulSoup(r.text, 'lxml')
            for a in soup.select('a'):
                text = clean(a.get_text())
                if len(text) < 6: continue
                if not any(kw in text for kw in ["考研", "专业", "院校", "分数", "调剂", "复试"]): continue
                if exists(cur, "qas", "title", text):
                    continue
                cur.execute(
                    "INSERT INTO qas (id, user_id, title, content, tags, status, view_count, answer_count, is_resolved, created_at) VALUES (%s, %s, %s, %s, %s, 'active', 0, 0, false, NOW())",
                    (new_id(), uid, text, f"来源: 考研帮", json.dumps(["考研帮", "考研"]))
                )
                total += cur.rowcount
            conn.commit()
            print(f"  考研帮: +{total}条")
    except Exception as e:
        print(f"  考研帮错误: {str(e)[:80]}")
        conn.rollback()
    cur.close()
    return total

# ========== 5. 研招网调剂 ==========
def crawl_yz(conn):
    print("\n[5/6] 研招网调剂")
    cur = conn.cursor()
    total = 0
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            r = c.get("https://yz.chsi.com.cn/yztj/", headers=HEADERS)
            soup = BeautifulSoup(r.text, 'lxml')
            for a in soup.select('a'):
                text = clean(a.get_text())
                href = a.get("href", "")
                if len(text) < 6: continue
                if not any(kw in text for kw in ["大学", "学院", "调剂", "招生", "硕士"]): continue
                if exists(cur, "grad_adjustment_info", "university_name", text):
                    continue
                cur.execute(
                    "INSERT INTO grad_adjustment_info (id, university_name, department, major_name, source_url, year, status, data_sources, created_at) VALUES (%s, %s, '待查', '待查', %s, 2026, 'active', %s, NOW())",
                    (new_id(), text, href, json.dumps(["研招网"]))
                )
                total += cur.rowcount
            conn.commit()
            print(f"  研招网: +{total}条")
    except Exception as e:
        print(f"  研招网错误: {str(e)[:80]}")
        conn.rollback()
    cur.close()
    return total

# ========== 6. 微博搜索 ==========
def crawl_weibo(conn):
    print("\n[6/6] 微博搜索")
    cur = conn.cursor()
    total = 0
    uid = None
    cur.execute("SELECT id FROM users LIMIT 1")
    r = cur.fetchone()
    if r: uid = r[0]
    for kw in ["考研", "国考", "求职"]:
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as c:
                r = c.get(f"https://s.weibo.com/weibo?q={kw}", headers=HEADERS)
                soup = BeautifulSoup(r.text, 'lxml')
                for post in soup.select('.txt, .txt-content, p')[:30]:
                    text = clean(post.get_text())
                    if len(text) < 15: continue
                    title = text[:100]
                    if exists(cur, "experience_posts", "title", title):
                        continue
                    cur.execute(
                        "INSERT INTO experience_posts (id, user_id, title, summary, content, category, is_anonymous, status, view_count, like_count, comment_count, tags, source_platform, created_at) VALUES (%s, %s, %s, %s, %s, 'general', true, 'approved', 0, 0, 0, %s, 'weibo', NOW())",
                        (new_id(), uid, title, text[:200], text, json.dumps([kw]))
                    )
                    total += cur.rowcount
                conn.commit()
                print(f"  微博[{kw}]: 累计{total}条")
                time.sleep(1)
        except Exception as e:
            print(f"  微博[{kw}]: {str(e)[:60]}")
            conn.rollback()
    cur.close()
    return total

if __name__ == "__main__":
    print(f"GradPath 综合爬虫 v6 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    conn = get_db()
    r = {}
    r["bilibili"] = crawl_bilibili(conn)
    r["github"] = crawl_github(conn)
    r["huatu"] = crawl_huatu(conn)
    r["kaoyan"] = crawl_kaoyan(conn)
    r["yz"] = crawl_yz(conn)
    r["weibo"] = crawl_weibo(conn)
    conn.close()
    print("\n" + "=" * 60)
    total = sum(r.values())
    for s, c in r.items(): print(f"  {s}: {c} 条")
    print(f"  总计新增: {total} 条")
