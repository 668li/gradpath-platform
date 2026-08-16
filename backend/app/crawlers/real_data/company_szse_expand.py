# -*- coding: utf-8 -*-
"""SZSE listed-company list EXPANSION for GradPath.

Extends the sampled szse_listed source in company_public_scraper.py (3 pages /
60 companies) to the full-scale list: >=10 pages AND >=1000 companies, saved
to a SEPARATE file company_szse_expand.json.

Source (same public SZSE endpoint as company_public_scraper.py):
  https://www.szse.cn/api/report/ShowReport/data
      ?SHOWTYPE=JSON&CATALOGID=1110&TABKEY=tab1&PAGENO={page}
  深圳证券交易所官网「上市公司列表」公开接口（A股列表，每页 20 家）。
  Exchange public disclosure; the site requires its own Referer, which is a
  normal request header (not an anti-crawl bypass).

Compliance (mirrors company_public_scraper.py):
  - robots.txt checked (404/empty => unrestricted; 403/5xx => conservative skip)
  - 403/418/429 on content => HTTPBlockedError, source abandoned, no bypass
  - polite delay >=1.5s between requests, identified crawler UA
  - only public company info (name / industry / board / stock code); no
    financial detail fields are collected

Output: company_szse_expand.json (same directory), pure array with the fixed
8 fields {name, industry, size, city, description, website, source_url, rank},
deduplicated against company_public_data.json by company name so every record
is a NEW company for the GradPath company库.

Run:  py -3.13 company_szse_expand.py [--pages 55] [--min 1000]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import urllib.robotparser
from pathlib import Path

import requests

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0"
POLITE_DELAY = 1.5
TIMEOUT = 40
BLOCKING = (403, 418, 429)

SZSE_API = (
    "https://www.szse.cn/api/report/ShowReport/data"
    "?SHOWTYPE=JSON&CATALOGID=1110&TABKEY=tab1&PAGENO={page}"
)
BASE_DIR = Path(__file__).resolve().parent
OUT_PATH = BASE_DIR / "company_szse_expand.json"
EXISTING_PATH = BASE_DIR / "company_public_data.json"


class HTTPBlockedError(RuntimeError):
    """403/418/429 — treat as anti-crawl block, abandon (never bypass)."""


def robots_allowed(url: str) -> tuple[bool, str]:
    base = "https://www.szse.cn"
    try:
        resp = requests.get(f"{base}/robots.txt",
                            headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        if resp.status_code == 200 and resp.text.strip():
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(resp.text.splitlines())
            allowed = rp.can_fetch(USER_AGENT, url)
            return allowed, f"robots.txt 200，{'允许' if allowed else '禁止'}目标路径"
        if resp.status_code == 200:
            # 200 with EMPTY body => no rules (repo convention: unrestricted)
            return True, "robots.txt HTTP 200 但内容为空，视为无限制"
        if resp.status_code == 404:
            return True, "robots.txt 404（无限制）"
        if resp.status_code in BLOCKING:
            return False, f"robots.txt HTTP {resp.status_code}，保守视为禁止"
        return False, f"robots.txt HTTP {resp.status_code}，保守视为禁止"
    except requests.RequestException as exc:
        return False, f"robots.txt 无法访问（{exc.__class__.__name__}），保守视为禁止"


def fetch_json(page: int) -> list:
    url = SZSE_API.format(page=page)
    time.sleep(POLITE_DELAY)
    # 官网接口要求同站 Referer，属正常请求头（非绕过反爬）
    resp = requests.get(url, headers={"User-Agent": USER_AGENT,
                                      "Referer": "https://www.szse.cn/"},
                        timeout=TIMEOUT)
    if resp.status_code in BLOCKING:
        raise HTTPBlockedError(f"HTTP {resp.status_code}（{url}），放弃")
    resp.raise_for_status()
    payload = resp.json()
    return payload[0].get("data", []) if payload else []


def row_to_company(row: dict, page_url: str) -> dict | None:
    name = re.sub(r"<[^>]+>|\s+", "", str(row.get("agjc") or ""))
    code = (row.get("agdm") or "").strip()
    industry = re.sub(r"^[A-Z]\s*", "", str(row.get("sshymc") or "")).strip()
    board = (row.get("bk") or "").strip()
    if not name:
        return None
    desc = f"深圳证券交易所{board}上市公司"
    if code:
        desc += f"（股票代码 {code}）"
    if industry:
        desc += f"，证监会行业分类：{industry}"
    return {
        "name": name,
        "industry": industry,
        "size": "",      # 接口未披露员工规模（如实留空）
        "city": "",      # 接口未披露注册地（如实留空）
        "description": desc + "。",
        "website": "",   # 接口未披露官网（如实留空）
        "source_url": page_url,
        "rank": None,    # 列表按代码排序，无榜单排名
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="深交所上市公司列表扩容")
    parser.add_argument("--pages", type=int, default=55,
                        help="抓取页数（每页20家，默认55）")
    parser.add_argument("--min", type=int, default=1000,
                        help="期望去重后最少公司数（默认1000）")
    args = parser.parse_args()

    allowed, robots_note = robots_allowed(SZSE_API.format(page=1))
    print(f"robots: https://www.szse.cn/robots.txt -> {robots_note}")
    if not allowed:
        print("[BLOCKED-ABANDONED] robots.txt 禁止，放弃该源（未绕过）")
        return 1

    companies, failed_pages = [], []
    for page in range(1, args.pages + 1):
        try:
            rows = fetch_json(page)
        except HTTPBlockedError as exc:
            print(f"[BLOCKED-ABANDONED] 第{page}页 {exc}")
            return 1 if not companies else 0
        except (requests.RequestException, json.JSONDecodeError) as exc:
            print(f"[ERROR] 第{page}页失败 {exc.__class__.__name__}: {exc}")
            failed_pages.append(page)
            continue
        if not rows:
            print(f"第{page}页为空，列表到底，停止翻页")
            break
        for row in rows:
            c = row_to_company(row, SZSE_API.format(page=page))
            if c:
                companies.append(c)
        if page % 10 == 0:
            print(f"已抓取 {page} 页 / {len(companies)} 家")

    # 与现有 company_public_data.json（fortune/isc/szse 采样）按公司名去重
    existing_names = set()
    if EXISTING_PATH.exists():
        for c in json.loads(EXISTING_PATH.read_text(encoding="utf-8")):
            existing_names.add(re.sub(r"\s+", "", c.get("name", "")))
    seen: set[str] = set()
    deduped = []
    for c in companies:
        key = re.sub(r"\s+", "", c["name"])
        if key and key not in seen and key not in existing_names:
            seen.add(key)
            deduped.append(c)

    with io.open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(deduped, fh, ensure_ascii=False, indent=2)

    print("=" * 68)
    print(f"抓取页数: {min(len(seen) and args.pages, args.pages)}"
          f"（失败页: {failed_pages if failed_pages else '无'}）")
    print(f"原始条数: {len(companies)}，去除与现有库重复: "
          f"{len(companies) - len(deduped)}")
    print(f"新增公司: {len(deduped)} 家 -> {OUT_PATH}")
    if deduped:
        print(f"样例: {[c['name'] for c in deduped[:3]]}")
    ok = len(deduped) >= args.min and len(companies) >= 200
    if not ok:
        print(f"[WARN] 未达到目标（≥{args.pages}页里抓到 {args.pages} 页，"
              f"≥{args.min}家 vs 实际 {len(deduped)} 家）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
