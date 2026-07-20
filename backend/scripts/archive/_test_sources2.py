import httpx

targets = {
    "v2ex_topics": "https://www.v2ex.com/api/topics/hot.json",
    "v2ex_node": "https://www.v2ex.com/go/qna",
    "offcn_guokao": "https://www.offcn.com/gkzt/",
    "huatu_guokao": "https://www.huatu.com/guojia/",
    "scs_gov": "https://www.scs.gov.cn/",
    "koolearn": "https://www.koolearn.com/",
    "yz_chsi": "https://yz.chsi.com.cn/",
    "sina_kaoyan": "https://kaoyan.sina.com.cn/",
    "weibo_kaoyan": "https://s.weibo.com/weibo?q=考研&typeall=1&suball=1",
}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for name, url in targets.items():
    try:
        with httpx.Client(timeout=8, follow_redirects=True) as client:
            r = client.get(url, headers=headers)
            print(f"{name}: {r.status_code} ({len(r.text)} bytes)")
    except Exception as e:
        print(f"{name}: ERROR {str(e)[:60]}")
