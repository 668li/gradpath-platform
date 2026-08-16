"""软科中国最好大学排名 API 采集器（2026-08-16）。

数据源：https://www.shanghairanking.cn/api/pub/v1/bcur?bcur_type=11&year=2026
  - 公开 JSON API，无鉴权，实测 HTTP 200（替代自爬软科榜单页）
  - 返回软科主榜 590 所（含全部 985/211/双一流院校）
字段：univNameCn/univNameEn/univTags[985,211,双一流]/province/score/ranking/rankOverall

合规（对齐 company_public_scraper.py 惯例）：
- 只取公开榜单数据（软科年度发布），入库标注来源；
- 采集前检查 robots.txt，被禁止则如实放弃；host 白名单校验（仅 shanghairanking.cn）；
- 单次请求即可拿全量，控频限速保留；
- 输出：backend/app/crawlers/real_data/ruanke_rankings.json
"""
from __future__ import annotations

import json
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0"
TIMEOUT = 30

API_URL = "https://www.shanghairanking.cn/api/pub/v1/bcur?bcur_type=11&year=2026"
ALLOWED_HOSTS = {"www.shanghairanking.cn", "shanghairanking.cn"}
OUT_FILE = Path(__file__).resolve().parent / "ruanke_rankings.json"


def _validate_outbound_url(url: str) -> None:
    """host 白名单校验：仅允许软科榜单 API 域名，拒绝其余主机（fail-safe）。"""
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise RuntimeError(f"目标主机 {host!r} 不在白名单，拒绝请求")


def _robots_allows(url: str) -> bool:
    """robots.txt 检查：不允许或取不到 → False（如实放弃）。"""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return False


def fetch() -> list[dict]:
    _validate_outbound_url(API_URL)
    if not _robots_allows(API_URL):
        print(f"robots 不允许访问 {API_URL}，如实放弃（不产出文件）")
        sys.exit(2)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Referer": "https://www.shanghairanking.cn/",
            "Accept": "application/json",
        }
    )
    resp = session.get(API_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    rankings = (payload.get("data") or {}).get("rankings") or []
    if not rankings:
        print("软科 API 返回空 rankings，如实放弃（不产出文件）")
        sys.exit(2)
    return rankings


def main() -> None:
    t0 = time.time()
    rows = fetch()
    time.sleep(1.0)  # 习惯性限速，单请求场景实际无影响
    OUT_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    n_985 = sum(1 for r in rows if "985" in (r.get("univTags") or []))
    n_211 = sum(1 for r in rows if "211" in (r.get("univTags") or []))
    n_syl = sum(1 for r in rows if "双一流" in (r.get("univTags") or []))
    print(
        f"软科主榜 {len(rows)} 所（985×{n_985} 211×{n_211} 双一流×{n_syl}）"
        f" → {OUT_FILE.name}（{time.time()-t0:.1f}s）"
    )


if __name__ == "__main__":
    main()
