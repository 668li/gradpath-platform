from playwright.sync_api import sync_playwright
import json

p = sync_playwright().start()
b = p.chromium.launch(headless=True)
page = b.new_page()
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
        page.goto(url, wait_until='domcontentloaded', timeout=10000)
        page.wait_for_timeout(2000)
        title = page.title()
        content = page.eval_on_selector_all('.RichContent-inner, .AnswerItem-content, .RichText', 'els => els.map(e => e.innerText).join("\\n")')
        if content:
            results.append({'title': title, 'content': content[:5000], 'url': url, 'source': 'zhihu', 'category': 'kaoyan_discussion'})
    except Exception as e:
        print(f'Error on {url}: {e}')

with open('/app/app/crawlers/real_data/zhihu_playwright.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False)
print(f'Zhihu Playwright: {len(results)} articles')
b.close()
p.stop()
