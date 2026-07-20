from playwright.sync_api import sync_playwright
import json

p = sync_playwright().start()
b = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
ctx = b.new_context(
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport={'width': 1920, 'height': 1080}
)
page = ctx.new_page()
results = []
urls = [
    'https://www.zhihu.com/question/19559043',
    'https://www.zhihu.com/question/360828645',
    'https://www.zhihu.com/question/572764289',
    'https://www.zhihu.com/question/320429063',
    'https://www.zhihu.com/question/400739911',
]
for url in urls:
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        page.wait_for_timeout(3000)
        title = page.title()
        # Try multiple selectors
        content = ''
        for sel in ['.RichContent-inner', '.AnswerItem-content', '.RichText', '.QuestionRichText', '.List-item .RichContent-inner', 'article', '.Post-RichText']:
            els = page.query_selector_all(sel)
            if els:
                content = '\n'.join([e.inner_text() for e in els])
                if content.strip():
                    print(f'  {url}: matched selector {sel}, len={len(content)}')
                    break
        if not content:
            # Fallback: grab body text
            body = page.query_selector('body')
            if body:
                content = body.inner_text()[:5000]
                print(f'  {url}: fallback body text, len={len(content)}')
        if content and len(content.strip()) > 50:
            results.append({'title': title, 'content': content[:5000], 'url': url, 'source': 'zhihu', 'category': 'kaoyan_discussion'})
        else:
            print(f'  {url}: no meaningful content found')
    except Exception as e:
        print(f'Error on {url}: {e}')

with open('/app/app/crawlers/real_data/zhihu_playwright.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False)
print(f'Zhihu Playwright: {len(results)} articles')
b.close()
p.stop()
