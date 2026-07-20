#!/usr/bin/env python3
"""学习方法知识爬取器"""
import httpx, json, time, psycopg2, re, uuid
from datetime import datetime
from html import unescape
from bs4 import BeautifulSoup

DB_URL = "postgresql://gradpath:changeme@db:5432/gradpath"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
def get_db(): return psycopg2.connect(DB_URL)
def clean(t):
    if not t: return ""
    t = re.sub(r'<[^>]+>', '', str(t))
    return re.sub(r'\s+', ' ', unescape(t)).strip()[:5000]
def new_id(): return str(uuid.uuid4())

def classify_tags(title, content):
    text = (title + " " + content).lower()
    tags = []
    if any(k in text for k in ["记忆","遗忘","艾宾浩斯","间隔","重复"]): tags.append("记忆科学")
    if any(k in text for k in ["番茄","时间管理","专注","碎片时间","日程"]): tags.append("时间管理")
    if any(k in text for k in ["费曼","主动学习","输出","教别人","实践"]): tags.append("学习策略")
    if any(k in text for k in ["习惯","21天","行为","坚持","打卡"]): tags.append("习惯养成")
    if any(k in text for k in ["思维导图","笔记","卡片","手写","整理"]): tags.append("笔记方法")
    if any(k in text for k in ["认知","元认知","注意力","大脑","神经"]): tags.append("认知科学")
    if any(k in text for k in ["睡眠","运动","饮食","心态","焦虑"]): tags.append("身心调节")
    if any(k in text for k in ["考试","备考","复习","真题","冲刺"]): tags.append("备考策略")
    return tags if tags else ["通用学习"]

def crawl_bilibili(conn):
    print("\n[B站] 学习方法视频")
    cur = conn.cursor()
    total = 0
    keywords = ["学习方法","认知科学","习惯养成","番茄工作法","费曼学习法","思维导图学习","时间管理","高效学习","记忆方法","备考策略"]
    for kw in keywords:
        try:
            url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&page=1"
            with httpx.Client(timeout=15) as c:
                r = c.get(url, headers=HEADERS)
                if r.status_code == 412: time.sleep(3); continue
                if r.status_code != 200: continue
                results = r.json().get("data",{}).get("result") or []
            count = 0
            for v in results[:20]:
                title = clean(v.get("title",""))
                desc = clean(v.get("description",""))
                author = v.get("author","")
                bvid = v.get("bvid","")
                content = f"【{kw}】{desc}\n\nUP主: {author}\nhttps://www.bilibili.com/video/{bvid}"
                tags = classify_tags(title, content)
                if not title: continue
                cur.execute("SELECT 1 FROM knowledge_articles WHERE title=%s LIMIT 1",(title,))
                if cur.fetchone(): continue
                cur.execute(
                    "INSERT INTO knowledge_articles (id,title,content,source,category,tags,metadata,is_published,created_at) VALUES (%s,%s,%s,'bilibili','学习方法',%s,%s,true,NOW())",
                    (new_id(), title, content, json.dumps(tags), json.dumps({"source_url":f"https://www.bilibili.com/video/{bvid}","author":author}))
                )
                count += cur.rowcount
            conn.commit()
            total += count
            print(f"  [{kw}] +{count}条")
            time.sleep(2)
        except Exception as e:
            print(f"  [{kw}] 错误: {str(e)[:50]}")
            conn.rollback()
    cur.close()
    return total

def crawl_github(conn):
    print("\n[GitHub] 学习方法资料")
    cur = conn.cursor()
    total = 0
    keywords = ["learning-methods","habit-tracker","study-techniques","spaced-repetition","pomodoro","mind-map","note-taking","metacognition"]
    for kw in keywords:
        try:
            url = f"https://api.github.com/search/repositories?q={kw}&sort=stars&per_page=15"
            with httpx.Client(timeout=15) as c:
                r = c.get(url, headers={**HEADERS,"Accept":"application/vnd.github.v3+json"})
                repos = r.json().get("items",[])
            count = 0
            for repo in repos:
                name = repo.get("name","")
                desc = repo.get("description","") or ""
                stars = repo.get("stargazers_count",0)
                html_url = repo.get("html_url","")
                content = f"{desc}\n\nStars: {stars}\n{html_url}"
                tags = classify_tags(name, desc)
                cur.execute("SELECT 1 FROM knowledge_articles WHERE title=%s LIMIT 1",(name,))
                if cur.fetchone(): continue
                cur.execute(
                    "INSERT INTO knowledge_articles (id,title,content,source,category,tags,metadata,is_published,created_at) VALUES (%s,%s,%s,'github','学习方法',%s,%s,true,NOW())",
                    (new_id(), name, content, json.dumps(tags), json.dumps({"source_url":html_url,"stars":stars}))
                )
                count += cur.rowcount
            conn.commit()
            total += count
            print(f"  [{kw}] +{count}条")
            time.sleep(1)
        except Exception as e:
            print(f"  [{kw}] 错误: {str(e)[:50]}")
            conn.rollback()
    cur.close()
    return total

def crawl_duckduckgo(conn):
    print("\n[DuckDuckGo] 学习方法文章")
    cur = conn.cursor()
    total = 0
    queries = [
        "site:zhihu.com 学习方法 科学",
        "site:jianshu.com 认知科学 学习",
        "site:mp.weixin.qq.com 学习策略 高效",
        "site:zhuanlan.zhihu.com 习惯养成 方法",
        "site:zhihu.com 费曼学习法 实践",
    ]
    for q in queries:
        try:
            url = f"https://html.duckduckgo.com/html/?q={q}"
            with httpx.Client(timeout=10, follow_redirects=True) as c:
                r = c.get(url, headers=HEADERS)
                soup = BeautifulSoup(r.text, 'lxml')
                results = soup.select('.result__a')
            count = 0
            for a in results[:10]:
                title = clean(a.get_text())
                href = a.get("href","")
                if not title or len(title) < 5: continue
                # DuckDuckGo returns redirect URLs, extract actual URL
                if "uddg=" in href:
                    import urllib.parse
                    href = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
                tags = classify_tags(title, title)
                cur.execute("SELECT 1 FROM knowledge_articles WHERE title=%s LIMIT 1",(title,))
                if cur.fetchone(): continue
                cur.execute(
                    "INSERT INTO knowledge_articles (id,title,content,source,category,tags,metadata,is_published,created_at) VALUES (%s,%s,%s,'web','学习方法',%s,%s,true,NOW())",
                    (new_id(), title, f"来源: DuckDuckGo搜索\n链接: {href}", json.dumps(tags), json.dumps({"source_url":href,"query":q}))
                )
                count += cur.rowcount
            conn.commit()
            total += count
            print(f"  [{q[:30]}...] +{count}条")
            time.sleep(1)
        except Exception as e:
            print(f"  [{q[:20]}] 错误: {str(e)[:50]}")
            conn.rollback()
    cur.close()
    return total

if __name__ == "__main__":
    print(f"学习方法知识爬取器 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    conn = get_db()
    r = {}
    r["B站"] = crawl_bilibili(conn)
    r["GitHub"] = crawl_github(conn)
    r["DuckDuckGo"] = crawl_duckduckgo(conn)
    conn.close()
    print("\n" + "=" * 60)
    for s,c in r.items(): print(f"  {s}: +{c}条")
    print(f"  总计: +{sum(r.values())}条")
