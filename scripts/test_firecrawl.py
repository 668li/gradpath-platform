# -*- coding: utf-8 -*-
"""测试Firecrawl API key是否可用"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

os.environ["FIRECRAWL_API_KEY"] = "fc-ec9fa1ce53474816bbbe0865cbfb3700"

try:
    from firecrawl import FirecrawlApp
    app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
    
    # Test scrape a simple page
    print("Testing Firecrawl scrape...")
    result = app.scrape_url("https://www.kaoyan.com/", params={"formats": ["markdown"]})
    
    if "markdown" in result:
        md = result["markdown"]
        print(f"SUCCESS! Got {len(md)} chars of markdown")
        print(f"First 500 chars:")
        print(md[:500])
    else:
        print(f"Result keys: {list(result.keys())}")
        print(f"Full result: {str(result)[:500]}")
        
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)[:200]}")
