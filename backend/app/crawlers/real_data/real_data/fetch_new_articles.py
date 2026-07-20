# -*- coding: utf-8 -*-
"""Fetch new kaoyan.com articles and merge into real_articles.json"""
import sys, json, time, os, urllib.request, re
sys.stdout.reconfigure(encoding='utf-8')

NEW_URLS = [
    ("26考研「专业课」如何背到滚瓜烂熟？", "https://www.kaoyan.com/experience/detail?uuid=eaff65cc5ef54fd985cb4124e553313e", "备考经验", "experience"),
    ("等等！26备考的你，先停下！", "https://www.kaoyan.com/experience/detail?uuid=b98c4545c6c04894acaa4b387e10163f", "备考经验", "experience"),
    ("考研大纲=划重点？大纲怎么用看这篇就够了", "https://www.kaoyan.com/experience/detail?uuid=9136ab9b59de43028cc7e9a40c1add86", "备考经验", "experience"),
    ("考研最后一个月，各学科保命指南！", "https://www.kaoyan.com/experience/detail?uuid=597c8eae321d4ed58f44bc67cd709db6", "备考经验", "experience"),
    ("考研英语平均分来了！25考研最后关头该怎么冲！", "https://www.kaoyan.com/experience/detail?uuid=155389d37de04a9ba1853c20c4ca96cb", "备考经验", "experience"),
    ("卷面这样的，一定得改啊！！！", "https://www.kaoyan.com/experience/detail?uuid=83657fa4c9324e15a42146d96dd908ae", "备考经验", "experience"),
    ("考研冲刺阶段，每天学习14小时够吗？！", "https://www.kaoyan.com/experience/detail?uuid=6bcfa318d1c740dcbd629439ea08dcce", "备考经验", "experience"),
    ("初试占比70%的宝藏院校，复试压力小！", "https://www.kaoyan.com/experience/detail?uuid=c8475e93c19c42de8b35d6ee8773ab56", "备考经验", "experience"),
    ("25考研，现在才开始备考的极限上岸规划！", "https://www.kaoyan.com/experience/detail?uuid=4dad4702ad234d678469c36e9fd4fa4b", "备考经验", "experience"),
    ("考研最后三个月，这份极限上岸计划请收好！", "https://www.kaoyan.com/experience/detail?uuid=ce00bd687e2347beabbf66f9ce4ea3b3", "备考经验", "experience"),
    ("拼命复习三个月，能考上研究生吗？", "https://www.kaoyan.com/experience/detail?uuid=913cae862d4a4643994bdd6511c00abe", "备考经验", "experience"),
    ("预报名结束！考研人接下来应该做什么？", "https://www.kaoyan.com/experience/detail?uuid=6d76e2b9167d47b68e93906f04a2af93", "备考经验", "experience"),
    ("24考研复试六大调剂新规", "https://www.kaoyan.com/adjust/1/9/4475f4e693914956bb7966b66e78a4c4", "调剂指南", "adjust"),
    ("调剂过程中可能会遇到的几方面问题", "https://www.kaoyan.com/adjust/1/9/82dac001fb3c43e695e63f6a84356194", "调剂指南", "adjust"),
    ("24考研调剂有哪些事项需要注意？", "https://www.kaoyan.com/adjust/1/9/f1c7f3c351134dff9a7d398ba3759692", "调剂指南", "adjust"),
    ("20条考研调剂经验，快来收藏！", "https://www.kaoyan.com/adjust/1/9/8f86f724560f40b7a7a99e466d71c6e9", "调剂指南", "adjust"),
    ("参加考研调剂有哪些基础要求？", "https://www.kaoyan.com/adjust/1/9/00384614726a46d4a42185c4812b9879", "调剂指南", "adjust"),
    ("难受！这些院校淘汰率最高82.8%！复试刷人超狠！", "https://www.kaoyan.com/adjust/1/9/c6545ce3c69346c4a94e7d34df6f914f", "调剂指南", "adjust"),
    ("措手不及！出复试线通知后两天内就复试！", "https://www.kaoyan.com/adjust/1/9/51eae20b285c45d7804b630cf441f6e9", "调剂指南", "adjust"),
    ("考研复试| 自我介绍速成攻略", "https://www.kaoyan.com/adjust/1/9/22247e6aab0149a4874bd1486de2e049", "调剂指南", "adjust"),
    ("调剂要从速，盘点考研调剂的3大渠道", "https://www.kaoyan.com/adjust/1/9/44041d7e53c24d6b930806171585a345", "调剂指南", "adjust"),
    ("【调剂专区】23考研调剂信息汇总（持续更新）", "https://www.kaoyan.com/adjust/1/9/178b9d6122454e229404bd08de4a0e38", "调剂指南", "adjust"),
    ("【调剂专区】23考研调剂信息汇总（定期更新）", "https://www.kaoyan.com/adjust/1/9/38bb3d9de8f2424fbfbcfa55f2455aac", "调剂指南", "adjust"),
]


def clean_text(text):
    """Remove navigation, ads, CSS/JS noise, footer content from fetched text."""
    # Remove common kaoyan.com noise
    markers = [
        "立即登录", "没有合适的帮你对接", "立即申请", "1w+学长学姐已入驻",
        "立即入驻", "关于我们", "发展历程", "商务合作", "服务条款", "隐私保护",
        "考研帮APP", "考研帮PLUS小程序", "考研帮-抖音", "考研网-公众号",
        "学而思考研-视频号", "学而思考研-小红书", "友情链接",
        "学而思托福", "学而思雅思", "学而思GRE", "学而思GMAT", "优路教育",
        "违法/不良信息举报邮箱", "广告投放与宣传QQ",
        "Copyright", "京ICP备", "京公网安备", "考研帮 版权所有",
        "上一篇:", "下一篇:",
    ]
    for marker in markers:
        idx = text.find(marker)
        if idx > 0:
            text = text[:idx]

    # Remove CSS/HTML noise patterns
    text = re.sub(r'\{[^}]*\}', '', text)
    text = re.sub(r'/\*!.*?\*/', '', text)
    text = re.sub(r'--tw-[^:]+:[^;]+;', '', text)
    text = re.sub(r'tailwindcss v[\d.]+\|.*', '', text)
    text = re.sub(r'font-feature-settings.*', '', text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()

    # Extract title from the text if present (skip navigation)
    lines = text.split('\n')
    content_lines = []
    skip_nav = True
    for line in lines:
        line = line.strip()
        if not line:
            if skip_nav:
                continue
            content_lines.append('')
            continue
        # Skip navigation/header lines
        if skip_nav:
            if '首页' in line or '院校信息' in line or '专业信息' in line or '历年真题' in line or '复习策略' in line or '复试调剂' in line or '备考经验' in line or '学长学姐' in line:
                skip_nav = False  # After nav, start collecting
                continue
            if '学而思考研帮' in line or '考研网（kaoyan.com）' in line:
                continue
        content_lines.append(line)

    text = '\n'.join(content_lines).strip()

    # Remove first nav line if still there
    if text.startswith('首页'):
        idx = text.find('\n')
        if idx > 0:
            text = text[idx:].strip()

    return text[:5000] if len(text) > 5000 else text


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="ignore")
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return ""


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "real_articles.json")

    # Load existing articles
    with open(json_path, "r", encoding="utf-8") as f:
        existing = json.load(f)
    existing_urls = {a["url"] for a in existing}
    print(f"Loaded {len(existing)} existing articles")

    new_count = 0
    for i, (title, url, category, page_type) in enumerate(NEW_URLS):
        if url in existing_urls:
            print(f"[{i+1}/{len(NEW_URLS)}] SKIP (already exists): {title}")
            continue

        print(f"[{i+1}/{len(NEW_URLS)}] Fetching: {title}")
        raw = fetch(url)
        if not raw:
            print(f"  FAILED to fetch, creating minimal entry")
            content = f"{title}\n\n内容暂时无法获取，请访问原文链接查看。"
        else:
            content = clean_text(raw)

        entry = {
            "title": title,
            "url": url,
            "category": category,
            "source": "kaoyan.com",
            "page_type": page_type,
            "content": content
        }
        existing.append(entry)
        existing_urls.add(url)
        new_count += 1
        print(f"  Content: {len(content)} chars")
        time.sleep(1.5)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Added {new_count} new articles. Total: {len(existing)} articles")
    print(f"Saved to: {json_path}")


if __name__ == "__main__":
    main()
