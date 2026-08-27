import json
import os
import time
from pathlib import Path

import requests

SESSION = "kaoyan-major-crawl"
ALL_MAJORS = []
PAGES_TO_CRAWL = 50
# 合规红线：守护进程地址 env 注入，禁止硬编码
DAEMON_URL = os.getenv("DAEMON_URL", "http://127.0.0.1:10086/command")


def send_command(action, args):
    payload = {"action": action, "args": args, "session": SESSION}
    resp = requests.post(DAEMON_URL, json=payload, timeout=30)
    return resp.json()


def extract_majors():
    code = """(() => {
        const main = document.querySelector('main') || document.body;
        const text = main.innerText;
        const regex = /([\\u4e00-\\u9fa5A-Za-z（）]+)\\s*开设院校\\s*\\n?\\s*专业代码[：:]([A-Z0-9a-z]+)\\s*\\n?\\s*专业类型[：:](.+)/g;
        const majors = [];
        let match;
        while ((match = regex.exec(text)) !== null) {
            majors.push({
                name: match[1].trim(),
                code: match[2].trim(),
                type: match[3].trim()
            });
        }
        return majors;
    })()"""
    result = send_command("evaluate", {"code": code})
    return result.get("data", {}).get("value", [])


def go_to_next_page():
    code = """(() => {
        const nextBtn = document.querySelector('button[aria-label="Go to next page"], .btn-next:not([disabled])');
        if (nextBtn) {
            nextBtn.click();
            return true;
        }
        return false;
    })()"""
    result = send_command("evaluate", {"code": code})
    return result.get("data", {}).get("value", False)


def go_to_page(page_num):
    code = f"""(() => {{
        const pageItems = document.querySelectorAll('.el-pager li, [class*=pager] li');
        for (const item of pageItems) {{
            if (item.textContent.trim() === '{page_num}') {{
                item.click();
                return true;
            }}
        }}
        return false;
    }})()"""
    result = send_command("evaluate", {"code": code})
    return result.get("data", {}).get("value", False)


# Navigate to the page first
print("Navigating to kaoyan.com/major...")
send_command(
    "navigate",
    {"url": "https://www.kaoyan.com/major", "newTab": True, "group_title": "kaoyan major crawl"},
)
time.sleep(4)

print(f"Crawling {PAGES_TO_CRAWL} pages...")

for page in range(1, PAGES_TO_CRAWL + 1):
    print(f"\n--- Page {page} ---")

    majors = extract_majors()
    print(f"Found {len(majors)} majors on page {page}")

    for m in majors:
        m["page"] = page
        m["source"] = "kaoyan.com"
        ALL_MAJORS.append(m)

    for m in majors[:3]:
        print(f"  {m['code']} - {m['name']} ({m['type']})")

    if page < PAGES_TO_CRAWL:
        success = go_to_next_page()
        if not success:
            print("No next page button, trying direct page navigation...")
            success = go_to_page(page + 1)

        if not success:
            print(f"Failed to navigate to page {page + 1}, stopping.")
            break

        time.sleep(2)

# Deduplicate by code
seen = set()
unique_majors = []
for m in ALL_MAJORS:
    key = (m["code"], m["name"])
    if key not in seen:
        seen.add(key)
        unique_majors.append(m)

# Save results
# 输出到脚本所在目录（Path(__file__)），禁止绝对路径硬编码
output_path = Path(__file__).resolve().parent / "major_crawled.json"
output = {
    "source": "kaoyan.com/major",
    "pages_crawled": PAGES_TO_CRAWL,
    "total_majors_raw": len(ALL_MAJORS),
    "total_majors_unique": len(unique_majors),
    "majors": unique_majors,
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\n=== DONE ===")
print(f"Pages crawled: {PAGES_TO_CRAWL}")
print(f"Total majors (raw): {len(ALL_MAJORS)}")
print(f"Total majors (unique): {len(unique_majors)}")
print(f"Saved to: {output_path}")

# Show stats by type
type_counts = {}
for m in unique_majors:
    t = m["type"]
    type_counts[t] = type_counts.get(t, 0) + 1
print("\nBy type:")
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")

# Show first 10
print("\nFirst 10 majors:")
for i, m in enumerate(unique_majors[:10]):
    print(f"  {i+1}. {m['code']} - {m['name']} ({m['type']})")
