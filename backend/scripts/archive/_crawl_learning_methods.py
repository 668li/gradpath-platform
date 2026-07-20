#!/usr/bin/env python3
"""学习方法知识爬取器 — 爬取认知科学、习惯养成、学习策略相关内容"""
import httpx, json, time, psycopg2, re, uuid
from datetime import datetime
from html import unescape
from bs4 import BeautifulSoup
import urllib.parse

DB_URL = "postgresql://gradpath:changeme@localhost:5432/gradpath"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def get_db():
    return psycopg2.connect(DB_URL)

def clean(t):
    if not t: return ""
    t = re.sub(r'<[^>]+>', '', str(t))
    return re.sub(r'\s+', ' ', unescape(t)).strip()[:5000]

def new_id():
    return str(uuid.uuid4())

# 自动分类tag
def classify_tag(title):
    tags = []
    title_lower = title.lower()
    if any(kw in title_lower for kw in ['记忆', '艾宾浩斯', '遗忘曲线', 'mnemonic']):
        tags.append('记忆科学')
    if any(kw in title_lower for kw in ['番茄', '时间管理', 'pomodoro']):
        tags.append('时间管理')
    if any(kw in title_lower for kw in ['费曼', '主动学习', '费曼学习法']):
        tags.append('学习策略')
    if any(kw in title_lower for kw in ['习惯', 'habit', '21天']):
        tags.append('习惯养成')
    if any(kw in title_lower for kw in ['思维导图', '笔记', 'mind map', 'note']):
        tags.append('笔记方法')
    if any(kw in title_lower for kw in ['认知', '元认知', 'cognitive']):
        tags.append('认知科学')
    if any(kw in title_lower for kw in ['睡眠', '运动', 'exercise', 'sleep']):
        tags.append('身心调节')
    if any(kw in title_lower for kw in ['考试', '复习', '备考', 'exam']):
        tags.append('备考策略')
    if not tags:
        tags.append('学习方法')
    return tags

# ========== B站学习视频 ==========
def crawl_bilibili(conn):
    print("\n[B站] 学习视频")
    cur = conn.cursor()
    total = 0
    search_keywords = [
        '学习方法', '认知科学', '习惯养成', '番茄工作法', 
        '费曼学习法', '思维导图学习'
    ]
    
    for keyword in search_keywords:
        try:
            url = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={urllib.parse.quote(keyword)}&page=1&pagesize=20"
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                r = client.get(url, headers=HEADERS)
                if r.status_code != 200:
                    print(f"  [{keyword}] 请求失败: {r.status_code}")
                    continue
                data = r.json()
                if data.get('code') != 0:
                    print(f"  [{keyword}] API错误: {data.get('message')}")
                    continue
                results = data.get('data', {}).get('result', [])
                for item in results[:20]:
                    title = clean(item.get('title', ''))
                    if not title or len(title) < 5:
                        continue
                    bvid = item.get('bvid', '')
                    author = item.get('author', '')
                    play = item.get('play', 0)
                    duration = item.get('duration', '')
                    source_url = f"https://www.bilibili.com/video/{bvid}" if bvid else ''
                    tags = classify_tag(title)
                    metadata = {
                        'source_url': source_url,
                        'author': author,
                        'play_count': play,
                        'duration': duration,
                        'keyword': keyword
                    }
                    cur.execute(
                        """INSERT INTO knowledge_articles (id, title, content, source, category, tags, metadata, is_published, created_at) 
                           SELECT %s, %s, %s, %s, '学习方法', %s, %s, true, NOW() 
                           WHERE NOT EXISTS (SELECT 1 FROM knowledge_articles WHERE title=%s)""",
                        (new_id(), title, f"【B站】{title}\n作者: {author}\n播放: {play}\n链接: {source_url}", 
                         'bilibili', json.dumps(tags), json.dumps(metadata), title)
                    )
                    total += cur.rowcount
            conn.commit()
            print(f"  [{keyword}] +{cur.rowcount}条")
            time.sleep(1.5)
        except Exception as e:
            print(f"  [{keyword}] 错误: {e}")
            conn.rollback()
    
    cur.close()
    return total

# ========== GitHub学习资料 ==========
def crawl_github(conn):
    print("\n[GitHub] 学习资料")
    cur = conn.cursor()
    total = 0
    search_queries = [
        'learning-methods', 'habit-tracker', 'study-techniques',
        'study-methods', 'learning-science'
    ]
    
    for query in search_queries:
        try:
            url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page=20"
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                r = client.get(url, headers=HEADERS)
                if r.status_code != 200:
                    print(f"  [{query}] 请求失败: {r.status_code}")
                    continue
                data = r.json()
                items = data.get('items', [])
                for item in items[:20]:
                    title = clean(item.get('name', ''))
                    description = clean(item.get('description', ''))
                    full_name = item.get('full_name', '')
                    html_url = item.get('html_url', '')
                    stars = item.get('stargazers_count', 0)
                    if not title or len(title) < 3:
                        continue
                    tags = classify_tag(title + ' ' + description)
                    metadata = {
                        'source_url': html_url,
                        'stars': stars,
                        'full_name': full_name,
                        'keyword': query
                    }
                    cur.execute(
                        """INSERT INTO knowledge_articles (id, title, content, source, category, tags, metadata, is_published, created_at) 
                           SELECT %s, %s, %s, %s, '学习方法', %s, %s, true, NOW() 
                           WHERE NOT EXISTS (SELECT 1 FROM knowledge_articles WHERE title=%s)""",
                        (new_id(), title, f"【GitHub】{title}\n{description}\n链接: {html_url}\nStars: {stars}", 
                         'github', json.dumps(tags), json.dumps(metadata), title)
                    )
                    total += cur.rowcount
            conn.commit()
            print(f"  [{query}] +{cur.rowcount}条")
            time.sleep(2)
        except Exception as e:
            print(f"  [{query}] 错误: {e}")
            conn.rollback()
    
    cur.close()
    return total

# ========== DuckDuckGo HTML搜索 ==========
def crawl_duckduckgo(conn):
    print("\n[DuckDuckGo] 搜索结果")
    cur = conn.cursor()
    total = 0
    searches = [
        ('site:zhihu.com 学习方法', '知乎'),
        ('site:jianshu.com 认知科学', '简书'),
        ('site:mp.weixin.qq.com 学习策略', '微信公众号')
    ]
    
    for query, source_name in searches:
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                r = client.get(url, headers=HEADERS)
                if r.status_code != 200:
                    print(f"  [{source_name}] 请求失败: {r.status_code}")
                    continue
                soup = BeautifulSoup(r.text, 'lxml')
                results = soup.select('.result__body')
                count = 0
                for result in results[:20]:
                    title_tag = result.select_one('.result__title a')
                    snippet_tag = result.select_one('.result__snippet')
                    if not title_tag:
                        continue
                    title = clean(title_tag.get_text())
                    link = title_tag.get('href', '')
                    snippet = clean(snippet_tag.get_text()) if snippet_tag else ''
                    if not title or len(title) < 5:
                        continue
                    tags = classify_tag(title + ' ' + snippet)
                    metadata = {
                        'source_url': link,
                        'snippet': snippet,
                        'source_name': source_name
                    }
                    cur.execute(
                        """INSERT INTO knowledge_articles (id, title, content, source, category, tags, metadata, is_published, created_at) 
                           SELECT %s, %s, %s, %s, '学习方法', %s, %s, true, NOW() 
                           WHERE NOT EXISTS (SELECT 1 FROM knowledge_articles WHERE title=%s)""",
                        (new_id(), title, f"【{source_name}】{title}\n{snippet}\n链接: {link}", 
                         source_name.lower(), json.dumps(tags), json.dumps(metadata), title)
                    )
                    count += cur.rowcount
                total += count
            conn.commit()
            print(f"  [{source_name}] +{count}条")
            time.sleep(1.5)
        except Exception as e:
            print(f"  [{source_name}] 错误: {e}")
            conn.rollback()
    
    cur.close()
    return total

# ========== 统计分类 ==========
def print_stats(conn):
    cur = conn.cursor()
    cur.execute("SELECT tags, COUNT(*) FROM knowledge_articles WHERE category='学习方法' GROUP BY tags")
    rows = cur.fetchall()
    print("\n分类统计:")
    for tags, count in rows:
        print(f"  {tags}: {count}条")
    cur.close()

if __name__ == "__main__":
    print(f"学习方法知识爬取器 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    conn = get_db()
    results = {}
    results['B站'] = crawl_bilibili(conn)
    results['GitHub'] = crawl_github(conn)
    results['DuckDuckGo'] = crawl_duckduckgo(conn)
    print_stats(conn)
    conn.close()
    print("\n" + "=" * 60)
    print("爬取结果汇总:")
    for source, count in results.items():
        print(f"  {source}: {count}条")
    print(f"  总计: {sum(results.values())}条")
