# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["FIRECRAWL_API_KEY"] = "fc-ec9fa1ce53474816bbbe0865cbfb3700"

from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

methods = [m for m in dir(app) if not m.startswith('_')]
print(f"Available methods: {methods}")

# Try scrape with new API
try:
    result = app.scrape("https://www.kaoyan.com/", formats=["markdown"])
    print(f"Result type: {type(result)}")
    if hasattr(result, 'markdown'):
        print(f"Markdown length: {len(result.markdown)}")
        print(result.markdown[:500])
    elif isinstance(result, dict):
        print(f"Keys: {list(result.keys())}")
    else:
        print(f"Result: {str(result)[:500]}")
except Exception as e:
    print(f"scrape error: {e}")
