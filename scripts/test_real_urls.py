# -*- coding: utf-8 -*-
"""真实爬取测试 - 寻找可访问的考研数据源"""
import sys, time, random
sys.stdout.reconfigure(encoding='utf-8')

def test_urls():
    from playwright.sync_api import sync_playwright
    
    # 测试真实可访问的考研相关URL
    test_urls = [
        ("考研帮首页", "https://www.kaoyan.com/"),
        ("研招网", "https://yz.chsi.com.cn/"),
        ("中国研究生招生信息网", "https://yz.chsi.com.cn/kyzx/"),
        ("考研网", "https://www.kaoyan.com.cn/"),
        ("新浪考研", "https://edu.sina.com.cn/kaoyan/"),
        ("新东方考研", "https://kaoyan.koolearn.com/"),
        ("考研帮院校库", "https://www.kaoyan.com/yuanxiao/"),
        ("B站考研", "https://search.bilibili.com/all?keyword=考研经验"),
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        
        for name, url in test_urls:
            page = ctx.new_page()
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=10000)
                status = resp.status if resp else "None"
                title = page.title()
                text_len = len(page.inner_text("body")) if status == 200 else 0
                print(f"[{status}] {name}: {url}")
                print(f"    Title: {title[:60]}")
                print(f"    Text length: {text_len}")
                if status == 200 and text_len > 500:
                    print(f"    >>> USABLE <<<")
            except Exception as e:
                print(f"[ERR] {name}: {str(e)[:80]}")
            finally:
                page.close()
                time.sleep(random.uniform(1, 2))
        
        browser.close()

if __name__ == "__main__":
    test_urls()
