# -*- coding: utf-8 -*-
"""资源导航候选链接批量实测脚本（RN-3/RN-4 前置）。

纪律（任务书 2026-10-03 约束 3/5）：
- 每条链接实测 HTTP 状态 + 页面 title（性质核对），记录写 sources 字段；
- 挂了/不达标的如实标 not_found，不预填不凑数；
- JS 挑战站不硬闯，如实记录；
- 只允许 http/https，拒绝 localhost/环回/私有保留地址（host 校验）。

固定输入 /tmp/resource_probe_input.json，固定输出 /tmp/resource_probe_result.json
（无 CLI 路径参数，规避路径穿越面）。
"""

from __future__ import annotations

import ipaddress
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

# Windows Python 解析不了 Git Bash 的 /tmp（已知坑），用绝对 Temp 路径
IN_PATH = Path(r"C:\Users\李勇谚\AppData\Local\Temp\resource_probe_input.json")
OUT_PATH = Path(r"C:\Users\李勇谚\AppData\Local\Temp\resource_probe_result.json")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
TIMEOUT = 20.0

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def _guard(url: str) -> None:
    """SSRF 防线：仅 http/https + 拒绝 localhost/环回/私有保留地址。"""
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"scheme 不允许: {p.scheme}")
    host = p.hostname or ""
    if host in ("localhost", "0.0.0.0", "::1", ""):
        raise ValueError(f"host 不允许: {host}")
    # Python 3.13 ip_address() 对非 IP 字面量抛裸 ValueError（非 AddressValueError）
    for fam_host in {host, host.strip("[]")}:
        try:
            ip = ipaddress.ip_address(fam_host)
        except ValueError:
            continue  # 域名而非 IP 字面量
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValueError(f"私有/保留地址不允许: {host}")


def probe(name: str, url: str, expect: str = "") -> dict:
    rec = {
        "name": name,
        "url": url,
        "expect": expect,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _guard(url)
    except ValueError as e:
        rec.update({"http_status": None, "verdict": "blocked_by_guard", "note": str(e)})
        return rec
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=TIMEOUT,
            headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
        ) as client:
            r = client.get(url)
        title = ""
        m = TITLE_RE.search(r.text[:20000] if r.text else "")
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()[:120]
        verdict = "ok" if r.status_code == 200 else "non_200"
        # JS 挑战站特征：极短正文 + challenge 关键词
        body = (r.text or "")[:3000].lower()
        if r.status_code in (403, 412, 488) or (
            r.status_code == 200
            and len(r.text or "") < 800
            and any(k in body for k in ("challenge", "verify", "captcha", "acw_sc__v2", "jschl"))
        ):
            verdict = "js_challenge"
        rec.update(
            {
                "http_status": r.status_code,
                "final_url": str(r.url),
                "title": title,
                "verdict": verdict,
            }
        )
    except Exception as e:  # noqa: BLE001 — 实测脚本须如实记录一切失败
        rec.update({"http_status": None, "verdict": "not_found", "note": f"{type(e).__name__}: {e}"[:200]})
    return rec


def probe_github_api(repo: str) -> dict:
    """GitHub 仓库活跃度/License 实测（RN-3 验收要求 repo 活跃度 pushed_at + License）。"""
    url = f"https://api.github.com/repos/{repo}"
    try:
        _guard(url)
        with httpx.Client(follow_redirects=True, timeout=TIMEOUT, headers={"User-Agent": UA}) as client:
            r = client.get(url)
        if r.status_code != 200:
            return {"repo": repo, "api_status": r.status_code, "verdict": "api_non_200"}
        d = r.json()
        return {
            "repo": repo,
            "api_status": 200,
            "stars": d.get("stargazers_count"),
            "pushed_at": d.get("pushed_at"),
            "archived": d.get("archived"),
            "license": (d.get("license") or {}).get("spdx_id"),
            "description": (d.get("description") or "")[:150],
            "html_url": d.get("html_url"),
        }
    except Exception as e:  # noqa: BLE001
        return {"repo": repo, "api_status": None, "verdict": f"api_error: {type(e).__name__}"}


def main() -> None:
    raw = json.loads(IN_PATH.read_text(encoding="utf-8"))
    results = {"pages": [], "repos": []}
    for item in raw.get("pages", []):
        rec = probe(item["name"], item["url"], item.get("expect", ""))
        print(
            f"[page] {rec['verdict']:>16} {str(rec.get('http_status') or '-'):>4} "
            f"{item['name']} -> {rec.get('title', '')[:60]}",
            flush=True,
        )
        results["pages"].append(rec)
    for repo in raw.get("repos", []):
        rec = probe_github_api(repo)
        print(f"[repo] stars={str(rec.get('stars', '-')):>7} pushed={rec.get('pushed_at', '-')} {repo}", flush=True)
        results["repos"].append(rec)
    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
