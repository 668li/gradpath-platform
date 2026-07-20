"""B站考研视频 Round 2 爬虫 — Playwright + API 双通道采集。"""
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# ── Playwright 采集 ──────────────────────────────────────────────

PLAYWRIGHT_KEYWORDS = [
    "考研数学经验",
    "考研英语经验",
    "考研政治经验",
    "考研复试经验",
    "考研调剂经验",
    "考研择校",
]

# ── API 采集 ─────────────────────────────────────────────────────

API_KEYWORDS = [
    "考研数学",
    "考研英语",
    "考研政治",
    "考研复试",
    "考研调剂",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://search.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

OUTPUT_PATH = Path(r"D:\职业规划\职业规划\backend\app\crawlers\real_data\bilibili_round2.json")


def _to_int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _clean_title(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


# ── 1. Playwright 采集 ───────────────────────────────────────────

def scrape_playwright() -> list[dict]:
    """通过 Playwright 模拟浏览器搜索 B 站，提取视频列表。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Playwright] 未安装 playwright，跳过 Playwright 采集")
        return []

    videos = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        page = context.new_page()

        # 先访问首页拿 Cookie
        try:
            page.goto("https://www.bilibili.com", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[Playwright] 首页预热失败: {e}")

        for kw in PLAYWRIGHT_KEYWORDS:
            url = f"https://search.bilibili.com/all?keyword={urllib.parse.quote(kw)}"
            print(f"[Playwright] 搜索: {kw}")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(4000)

                # 尝试多种选择器
                selectors = [
                    ".video-list-item",
                    ".video.i_wrapper",
                    "li[data-aid]",
                    ".search-content .video-list li",
                    "#video-list li",
                    "section[class*='video'] li",
                ]
                items = []
                for sel in selectors:
                    items = page.query_selector_all(sel)
                    if items:
                        print(f"  选择器 '{sel}' 匹配 {len(items)} 个")
                        break

                if not items:
                    # 尝试通过 JS 提取所有带链接的视频卡片
                    items_data = page.evaluate("""() => {
                        const results = [];
                        // 查找所有包含 /video/ 链接的卡片
                        document.querySelectorAll('a[href*="/video/"]').forEach(a => {
                            const href = a.href;
                            const title = a.getAttribute('title') || a.textContent.trim();
                            if (title && href.includes('/video/')) {
                                results.push({title, href});
                            }
                        });
                        return results;
                    }""")
                    for d in items_data:
                        bvid_m = re.search(r"(BV\w+)", d.get("href", ""))
                        bvid = bvid_m.group(1) if bvid_m else ""
                        if not bvid:
                            continue
                        # 避免重复
                        if any(v.get("bvid") == bvid for v in videos):
                            continue
                        videos.append({
                            "title": d["title"][:200],
                            "author": "",
                            "views": 0,
                            "description": "",
                            "url": f"https://www.bilibili.com/video/{bvid}",
                            "bvid": bvid,
                            "keyword": kw,
                            "source": "bilibili_playwright",
                        })
                    print(f"  JS 方式提取 {len(items_data)} 条")
                    time.sleep(0.5)
                    continue

                for item in items:
                    try:
                        title_el = item.query_selector("a[title]") or item.query_selector(".title")
                        title = ""
                        if title_el:
                            title = title_el.get_attribute("title") or title_el.inner_text()
                        if not title:
                            continue

                        author_el = item.query_selector(".up-name") or item.query_selector(".name")
                        author = author_el.inner_text().strip() if author_el else ""

                        view_el = item.query_selector(".play-text") or item.query_selector(".view")
                        views_text = view_el.inner_text().strip() if view_el else "0"
                        views = _parse_view_count(views_text)

                        desc_el = item.query_selector(".desc") or item.query_selector(".content-desc")
                        desc = desc_el.inner_text().strip() if desc_el else ""

                        link_el = item.query_selector("a[href*='video']")
                        href = link_el.get_attribute("href") if link_el else ""
                        bvid = ""
                        if href:
                            m = re.search(r"(BV\w+)", href)
                            if m:
                                bvid = m.group(1)

                        videos.append({
                            "title": title,
                            "author": author,
                            "views": views,
                            "description": desc,
                            "url": f"https://www.bilibili.com/video/{bvid}" if bvid else href,
                            "bvid": bvid,
                            "keyword": kw,
                            "source": "bilibili_playwright",
                        })
                    except Exception as e:
                        print(f"  解析单条视频出错: {e}")
                        continue

                print(f"  解析到 {len(items)} 条")

            except Exception as e:
                print(f"  [Playwright] 搜索 {kw} 失败: {e}")

            time.sleep(0.5)

        browser.close()

    return videos


def _parse_view_count(text: str) -> int:
    """解析播放量文本，如 '1.2万' -> 12000。"""
    text = text.strip().replace(",", "")
    if "万" in text:
        try:
            return int(float(text.replace("万", "")) * 10000)
        except ValueError:
            return 0
    if "亿" in text:
        try:
            return int(float(text.replace("亿", "")) * 100000000)
        except ValueError:
            return 0
    return _to_int(text)


# ── 2. API 采集 ──────────────────────────────────────────────────

def scrape_api() -> list[dict]:
    """通过 B站搜索 API 直接获取视频数据。"""
    videos = []

    # 先访问首页预热
    try:
        req = urllib.request.Request("https://www.bilibili.com", headers=HEADERS)
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:
        print(f"[API] 首页预热失败: {e}")

    for kw in API_KEYWORDS:
        encoded_kw = urllib.parse.quote(kw)
        url = (
            f"https://api.bilibili.com/x/web-interface/search/type"
            f"?keyword={encoded_kw}&search_type=video&page=1&pagesize=50"
        )
        print(f"[API] 搜索: {kw}")
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))

            if data.get("code") != 0:
                print(f"  API 错误: code={data.get('code')}, msg={data.get('message')}")
                continue

            results = data.get("data", {}).get("result", [])
            print(f"  获取 {len(results)} 条结果")

            for item in results:
                title = _clean_title(item.get("title", ""))
                bvid = item.get("bvid", "")
                arcurl = item.get("arcurl", "")
                desc = item.get("description", "") or item.get("desc", "")
                tags = [t.strip() for t in (item.get("tag", "") or "").split(",") if t.strip()]

                videos.append({
                    "title": title,
                    "author": item.get("author", ""),
                    "views": _to_int(item.get("play")),
                    "danmaku": _to_int(item.get("video_review")),
                    "description": desc,
                    "duration": item.get("duration", ""),
                    "pub_date": item.get("pubdate", 0),
                    "url": arcurl or f"https://www.bilibili.com/video/{bvid}",
                    "bvid": bvid,
                    "keyword": kw,
                    "source": "bilibili_api",
                    "tags": tags,
                })

        except Exception as e:
            print(f"  [API] 搜索 {kw} 失败: {e}")

        time.sleep(0.5)

    return videos


# ── 主入口 ───────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("B站考研视频 Round 2 爬虫")
    print("=" * 60)

    pw_videos = scrape_playwright()
    api_videos = scrape_api()

    # 合并去重（按 bvid 去重）
    seen_bvids = set()
    all_videos = []
    for v in pw_videos + api_videos:
        bvid = v.get("bvid", "")
        if bvid and bvid in seen_bvids:
            continue
        if bvid:
            seen_bvids.add(bvid)
        all_videos.append(v)

    result = {
        "source": "bilibili_round2",
        "keywords_playwright": PLAYWRIGHT_KEYWORDS,
        "keywords_api": API_KEYWORDS,
        "count": len(all_videos),
        "playwright_count": len(pw_videos),
        "api_count": len(api_videos),
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "videos": all_videos,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Playwright 采集: {len(pw_videos)} 条")
    print(f"API 采集: {len(api_videos)} 条")
    print(f"去重后总计: {len(all_videos)} 条")
    print(f"已保存到: {OUTPUT_PATH}")
    print(f"{'=' * 60}")

    return all_videos


if __name__ == "__main__":
    main()
