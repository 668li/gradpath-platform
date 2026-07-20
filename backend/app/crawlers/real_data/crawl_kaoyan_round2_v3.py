import os, json, re, time, urllib.request
from html import unescape

BASE_URL = "https://www.kaoyan.com"

list_pages = {
    "experience": "https://www.kaoyan.com/experience/",
    "news": "https://www.kaoyan.com/news/list/1/9370",
    "wiki": "https://www.kaoyan.com/news/list/1/3946"
}

all_articles = []
seen_urls = set()

def extract_article_links(html_content, category):
    links = []
    href_pattern = r'href="([^"]*)"'
    hrefs = re.findall(href_pattern, html_content)
    
    for href in hrefs:
        href = unescape(href)
        
        if category == "experience" and '/experience/detail' in href:
            uuid_match = re.search(r'uuid=([^&]+)', href)
            if uuid_match:
                uuid = uuid_match.group(1)
                url = f"{BASE_URL}/experience/detail?uuid={uuid}"
                if url not in seen_urls:
                    seen_urls.add(url)
                    links.append({"url": url, "category": category})
        elif category in ["news", "wiki"] and '/article/1/' in href:
            article_match = re.search(r'/article/1/(\d+)/([a-f0-9]+)', href)
            if article_match:
                cat_id = article_match.group(1)
                article_id = article_match.group(2)
                url = f"{BASE_URL}/article/1/{cat_id}/{article_id}"
                if url not in seen_urls:
                    seen_urls.add(url)
                    links.append({"url": url, "category": category})
    
    return links

def fetch_article(url, category):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        title = unescape(title_match.group(1).strip()) if title_match else ""
        
        article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
        if article_match:
            content_html = article_match.group(1)
        else:
            content_html = html
        
        content = re.sub(r'<script[^>]*>.*?</script>', '', content_html, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        if len(content) > 200:
            return {
                "url": url,
                "title": title,
                "content": content[:50000],
                "char_count": len(content),
                "category": category
            }
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
    return None

print("=" * 60)
print("Fetching list pages...")
print("=" * 60)

for category, url in list_pages.items():
    print(f"\nFetching {category} list page...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        links = extract_article_links(html, category)
        print(f"  Found {len(links)} article links in {category}")
        
        for link in links[:30]:
            print(f"  Fetching: {link['url'][:60]}...")
            article = fetch_article(link['url'], link['category'])
            if article:
                all_articles.append(article)
                print(f"    -> {article['char_count']} chars, title: {article['title'][:40]}")
            time.sleep(0.3)
            
    except Exception as e:
        print(f"  Error fetching {category} list: {e}")

all_articles.sort(key=lambda x: x["char_count"], reverse=True)

total_chars = sum(a["char_count"] for a in all_articles)

output_path = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\kaoyan_round2.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_articles, f, ensure_ascii=False, indent=2)

print(f"\n{'=' * 60}")
print(f"SUMMARY")
print(f"{'=' * 60}")
print(f"Total articles fetched: {len(all_articles)}")
print(f"Total characters: {total_chars:,}")

categories = {}
for a in all_articles:
    cat = a["category"]
    if cat not in categories:
        categories[cat] = {"count": 0, "chars": 0}
    categories[cat]["count"] += 1
    categories[cat]["chars"] += a["char_count"]

print("\nBy category:")
for cat, stats in categories.items():
    print(f"  {cat}: {stats['count']} articles, {stats['chars']:,} chars")

print(f"\nSaved to: {output_path}")

print("\nTop 10 articles:")
for i, a in enumerate(all_articles[:10]):
    t = (a["title"] or "(no title)")[:50]
    print(f"  {i+1}. [{a['char_count']:,} chars] [{a['category']}] {t}")