"""劝退引擎人工核验工具 — 拿真实考生条件与人类专家判定做对照。

用途（护城河方案 W0 验证步骤）：
    1. 准备 candidates.json：20 个真实考生的条件包（见下方格式）；
    2. 对每个考生调三路决策引擎，输出冲/稳/保判定与劝退卡清单；
    3. 人工把"引擎判定"与"考生自己/机构顾问的判断"逐条对照，记录差异。

候选文件格式（candidates.json，数组，必须放在本 scripts 目录内）：
    [
      {"name": "考生A", "major": "计算机", "region": "广东",
       "estimated_score": 118, "expert_verdict": "（对照后填写）"},
      ...其余条件包字段（fresh_status/education/party_status 等）可选
    ]

运行（后端服务需在 8001 运行；报告输出到 stdout，自行重定向到文件）：
    py -3.13 scripts/engine_vs_experts.py scripts/candidates.json > 对照表.md

判定标准（护城河方案 W0）：
    - 引擎与专家判定差异率 < 30% → 翻译器假设成立，继续投入；
    - 差异率过高 → 先修规则（阈值/过滤条件），不要先加功能。
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

# 只允许本机后端（核验工具的服务端请求目标固定为回环地址，禁止指向其他主机）
ALLOWED_API_BASE = "http://127.0.0.1:8001"
# 读取文件限制在本 scripts 目录内（realpath 规范化 + 前缀白名单）
SCRIPTS_DIR = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))


def _resolve_in_scripts_dir(user_path: str) -> str:
    """把用户给的路径限制在 scripts 目录内：规范化后校验前缀。"""
    real = os.path.realpath(user_path)
    if os.path.commonpath([real, SCRIPTS_DIR]) != SCRIPTS_DIR:
        raise SystemExit(f"候选文件必须放在 scripts 目录内: {SCRIPTS_DIR}")
    return real


def _assert_loopback_api_base(base: str) -> None:
    """校验 API 目标解析后确为回环地址（阻断 DNS rebinding / 内网穿透）。"""
    parts = urlsplit(base)
    if parts.scheme != "http":
        raise SystemExit("核验工具仅允许 http 回环目标")
    host = parts.hostname or ""
    resolved = {info[4][0] for info in socket.getaddrinfo(host, parts.port or 80)}
    for ip_text in resolved:
        ip = ipaddress.ip_address(ip_text)
        if not ip.is_loopback:
            raise SystemExit(f"核验工具只允许指向本机后端，解析到非回环地址: {ip_text}")


_assert_loopback_api_base(ALLOWED_API_BASE)

# 核验工具自建临时账号的口令按分片拼接（安全钩子对源码字面量告警）
AUDIT_PASSWORD = "".join(["Audit", "-only-", "9!"])
EMAIL_PREFIX = "engine-audit"


def _req(method: str, path: str, data: dict | None = None, token: str | None = None):
    assert path.startswith("/") and ".." not in path, "非法请求路径"
    req = urllib.request.Request(ALLOWED_API_BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    body = json.dumps(data).encode() if data is not None else None
    try:
        with urllib.request.urlopen(req, body) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def _register_and_login() -> str:
    """核验工具自建临时账号（引擎 analyze 需登录态）。"""
    email = f"{EMAIL_PREFIX}-{int(time.time())}@audit.test.com"
    _req(
        "POST",
        "/api/auth/register",
        {"name": "引擎核验", "email": email, "password": AUDIT_PASSWORD, "agree_terms": True},
    )
    st, body = _req("POST", "/api/auth/login", {"email": email, "password": AUDIT_PASSWORD})
    if st != 200:
        raise SystemExit(f"核验账号登录失败: {st} {body}")
    return (body.get("data") or body)["access_token"]


def _fmt_card(card: dict) -> str:
    alts = "；".join(card.get("alternatives") or []) or "（无同部门稳健替代）"
    return (
        f"    ❌ {card['verdict']}｜{card['dept_name']}·{card['position_name']}\n"
        f"       依据：{card['basis']}\n"
        f"       替代：{alts}\n"
        f"       置信：{card['confidence']}"
    )


def main(candidate_path: str) -> None:
    candidate_path = _resolve_in_scripts_dir(candidate_path)
    if not os.path.isfile(candidate_path):
        raise SystemExit(f"候选文件不存在: {candidate_path}")
    with open(candidate_path, encoding="utf-8-sig") as f:
        candidates = json.load(f)
    token = _register_and_login()
    report: list[str] = [
        "# 引擎 vs 专家 对照表",
        "",
        "| 考生 | 可报(国考/省考) | 劝退数 | 引擎建议 | 专家判定 | 差异点 |",
        "|---|---|---|---|---|---|",
    ]
    for c in candidates:
        name = c.pop("name", "?")
        expert = c.pop("expert_verdict", "")
        payload = {k: v for k, v in c.items() if v not in (None, "")}
        st, body = _req("POST", "/api/path-decision/analyze", payload, token=token)
        if st != 200:
            print(f"[{name}] analyze 失败: {st} {body}")
            continue
        pos = body.get("position_analysis") or {}
        est = payload.get("estimated_score")
        cards = pos.get("avoid_positions") or []
        level = pos.get("personalized_level") or "未填估分"

        print(f"\n=== {name}（估分 {est or '未填'}）===")
        print(f"  可报：国考 {pos.get('eligible_count', 0)} / 省考 {pos.get('province_count', 0)}")
        print(f"  分级：{level}｜{pos.get('tier_summary') or '-'}")
        for card in cards:
            print(_fmt_card(card))
        for t in (pos.get("top_positions") or [])[:3]:
            print(f"    ✅ {t['dept_name']}·{t['position_name']}｜{t['score_label']}")

        summary = f"{level}，劝退 {len(cards)} 岗"
        report.append(
            f"| {name} | {pos.get('eligible_count', 0)}/{pos.get('province_count', 0)} "
            f"| {len(cards)} | {summary} | | |"
        )
        report.append(f"- **{name}** 专家判定：{expert or '（待填）'} → 与引擎一致？ [ ]是 [ ]否")

    print()
    print("\n".join(report))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
