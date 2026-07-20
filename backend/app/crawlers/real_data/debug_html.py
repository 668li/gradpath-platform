import urllib.request
import re

urls = [
    ("experience", "https://www.kaoyan.com/experience/"),
    ("news", "https://www.kaoyan.com/news/list/1/9370"),
    ("wiki", "https://www.kaoyan.com/news/list/1/3946")
]

for name, url in urls:
    print(f"\n{'=' * 60}")
    print(f"Fetching {name}: {url}")
    print(f"{'=' * 60}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8', errors='ignore')
        
        print(f"Length: {len(content)} chars")
        
        links = re.findall(r'href="([^"]*)"', content)
        print(f"Found {len(links)} href links")
        
        article_links = [l for l in links if '/article/' in l or '/experience/detail' in l]
        print(f"Article/experience links: {len(article_links)}")
        
        for link in article_links[:5]:
            print(f"  {link}")
            
        if not article_links:
            print("\nFirst 2000 chars of HTML:")
            print(content[:2000])
            
    except Exception as e:
        print(f"Error: {e}")