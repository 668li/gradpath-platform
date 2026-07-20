import os
import json
from firecrawl import FirecrawlApp

os.environ["FIRECRAWL_API_KEY"] = "fc-ec9fa1ce53474816bbbe0865cbfb3700"
app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

# Test crawl to inspect object structure
result = app.crawl("https://www.kaoyan.com/", limit=2, scrape_options={"formats": ["markdown"]})

print("Type of result:", type(result))
print("Dir of result:", [a for a in dir(result) if not a.startswith('_')])

if hasattr(result, 'data'):
    print("\nType of result.data:", type(result.data))
    if result.data:
        page = result.data[0]
        print("\nType of page:", type(page))
        print("Dir of page:", [a for a in dir(page) if not a.startswith('_')])
        
        # Try to get markdown
        md = getattr(page, 'markdown', None)
        print(f"\npage.markdown type: {type(md)}, len: {len(md) if md else 0}")
        if md:
            print(f"First 500 chars: {md[:500]}")
        
        # Try to get metadata
        meta = getattr(page, 'metadata', None)
        print(f"\npage.metadata type: {type(meta)}")
        if meta:
            print(f"Dir of metadata: {[a for a in dir(meta) if not a.startswith('_')]}")
            source_url = getattr(meta, 'sourceURL', None) or getattr(meta, 'url', None)
            print(f"sourceURL: {source_url}")
