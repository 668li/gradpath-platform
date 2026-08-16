# -*- coding: utf-8 -*-
"""Position-granularity salary benchmark scraper for GradPath.

Collects REAL, traceable position-level wage-price statistics from PUBLIC
government announcements only (人社局「人力资源市场工资指导价位/工资价位」公告,
公告附件 PDF 内含 分职业 x 10%/25%/50%/75%/90% 分位数价位表).

Sources (all verified during research, robots.txt checked at runtime):
  1. 广州市人社局《广州市2025年人力资源市场工资价位及2024年企业人工成本信息》
     - 公告页: https://rsj.gz.gov.cn/zwdt/tzgg/content/post_10619688.html
     - 附件 PDF: 分职业工资价位 (约170个职业) + “羊城家政”分职业工资价位
     - 前言注明调查时期指标为 2024-01-01 至 2024-12-31 => data year 2024
     - robots.txt: HTTP 404 => 无限制
  2. 深圳市人社局《深圳市2025年人力资源市场工资价位及行业人工成本信息》
     - 公告页: https://hrss.sz.gov.cn/xxgk/tjsj/zxtj/content/post_12735120.html
     - 附件 PDF: 整体工资价位(四)分学历与工龄 (学历x工龄, 33行) +
       (五)分职业细类 (约160个职业细类)
     - 编制说明注明调查时期指标为 2024-01-01 至 2024-12-31 => data year 2024
     - robots.txt: HTTP 404 => 无限制
  3. 杭州市人社局《杭州市2023年企业薪酬调查信息》
     - 官方 PDF (浙江政务网 JCMS 附件域 zjjcmspublic...cloud.zj.gov.cn):
       https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/
       jcms_files/jcms1/web3163/site/attach/0/8de07211fbc54b69b37cb7c62f3ddc47.pdf
     - 一、不同职业小类企业从业人员工资价位(2023年) => data year 2023
     - robots.txt: HTTP 404 => 无限制

Abandoned sources (honest record, 未绕过):
  - 苏州市人社局 hrss.suzhou.gov.cn: robots.txt 与列表页均 302 跳转主页,
    公告内容不可达 => 放弃
  - 北京市人社局: 以新闻稿形式发布《薪酬数据报告》, 未见公开分职业明细表
  - 成都市: 由四川省人社厅以“川渝地区”形式联合发布, 本轮未定位到可解析明细页
  - yz.chsi.com.cn (研招网) / 任何登录内容: 未触碰

Compliance (mirrors salary_gov_scraper.py):
  - robots.txt checked per host (404 => unrestricted); Disallow match => skip
  - 403/418/429 on content => HTTPBlockedError, source abandoned, no bypass
  - 1.5s polite delay between HTTP requests, identified crawler UA
  - every record carries source_url; values copied verbatim from公告原文

Percentile mapping: 10% -> salary_min, 50% -> salary_median, 90% -> salary_max.
(All tables in scope are 5-percentile tables; no single-value fallback needed.)
Education-tenure table (深圳 分学历与工龄): 学历 -> position, 工龄 ->
experience_level (1年以下/2-3年/4-5年/6-10年/11年以上), 学历合计行 -> 不限.

Output: salary_position_data.json (same directory)
Record fields: {position, city, experience_level, salary_min, salary_median,
                salary_max, year, source, source_url, category, unit}

Run:  py -3.13 salary_position_scraper.py
"""
import json
import os
import re
import sys
import time
from urllib.parse import urlsplit

import requests

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF (fitz) required: py -3.13 -m pip install pymupdf") from exc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "salary_position_data.json")
PDF_CACHE_DIR = os.path.join(BASE_DIR, "pdf_cache")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
REQUEST_TIMEOUT = 30
POLITE_DELAY = 1.5  # seconds between HTTP requests

BLOCKING_STATUSES = (403, 418, 429)


class HTTPBlockedError(RuntimeError):
    """Raised on 403/418/429 — source must be abandoned, never bypassed."""


# ---------------------------------------------------------------------------
# HTTP layer (robots-aware, rate-limited)
# ---------------------------------------------------------------------------

_LAST_REQUEST_HOST = {"host": None, "ts": 0.0}
ROBOTS_NOTES = {}


def _politeness_wait(url):
    host = urlsplit(url).netloc
    if _LAST_REQUEST_HOST["host"] == host:
        elapsed = time.time() - _LAST_REQUEST_HOST["ts"]
        if elapsed < POLITE_DELAY:
            time.sleep(POLITE_DELAY - elapsed)
    _LAST_REQUEST_HOST["host"] = host
    _LAST_REQUEST_HOST["ts"] = time.time()


def _requests_get(url):
    """GET with a documented one-shot https->http fallback.

    hrss.sz.gov.cn HTTPS fails the Python/OpenSSL 3.0 handshake
    (BAD_ECPOINT) while browsers and Schannel-based clients succeed —
    a client TLS quirk, not a server block. The host serves the identical
    public content over plain HTTP, so we retry the SAME path over http
    once. 403/418/429 are never retried or bypassed.
    """
    try:
        return requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.SSLError:
        fallback = "http://" + url.split("://", 1)[1]
        if fallback == url:
            raise
        ROBOTS_NOTES.setdefault(
            "note-ssl-fallback",
            "hrss.sz.gov.cn https handshake fails under Python/OpenSSL3 "
            "(BAD_ECPOINT); identical public pages fetched via http "
            "(robots.txt 404 on both schemes, verified)")
        return requests.get(fallback, headers=HEADERS, timeout=REQUEST_TIMEOUT)


def check_robots(url):
    """Return (allowed, note). 404 => unrestricted (per repo convention)."""
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        _politeness_wait(robots_url)
        resp = _requests_get(robots_url)
        if resp.status_code == 404:
            return True, "no robots.txt (404) -> unrestricted"
        if resp.status_code in BLOCKING_STATUSES:
            # robots endpoint itself blocked; be conservative but do not
            # auto-bypass: still attempt the public document once, and let
            # the content response decide (recorded either way).
            return True, f"robots.txt HTTP {resp.status_code} (non-standard)"
        if resp.status_code == 200:
            path = parts.path or "/"
            for line in resp.text.splitlines():
                m = re.match(r"(?i)disallow\s*:\s*(\S*)", line.strip())
                if m and m.group(1) and path.startswith(m.group(1)):
                    return False, f"robots.txt Disallow {m.group(1)} matches path"
            return True, "robots.txt present, no matching Disallow"
        return True, f"robots.txt HTTP {resp.status_code}"
    except Exception as exc:  # noqa: BLE001
        return True, f"robots check failed: {exc}"


def http_get(url, binary=False):
    allowed, note = check_robots(url)
    origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}"
    ROBOTS_NOTES.setdefault(origin, note)
    if not allowed:
        raise HTTPBlockedError(f"robots.txt disallows {url} ({note})")
    _politeness_wait(url)
    resp = _requests_get(url)
    if resp.status_code in BLOCKING_STATUSES:
        raise HTTPBlockedError(f"HTTP {resp.status_code} for {url} -> abandoned")
    resp.raise_for_status()
    if binary:
        return resp.content
    if resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "ascii"):
        resp.encoding = "utf-8"
    return resp.text


def download_pdf(url, filename):
    """Download announcement PDF into cache dir (reuses existing file)."""
    os.makedirs(PDF_CACHE_DIR, exist_ok=True)
    path = os.path.join(PDF_CACHE_DIR, filename)
    if os.path.exists(path) and os.path.getsize(path) > 1024:
        return path, "cached"
    data = http_get(url, binary=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path, "downloaded"


def find_pdf_links(html):
    return sorted(set(re.findall(r'href="([^"]+\.pdf[^"]*)"', html, re.I)))


# ---------------------------------------------------------------------------
# PDF percentile-table parser
# ---------------------------------------------------------------------------
# Layout (identical family across the three PDFs), text extraction yields
# tokens in reading order:
#   ... 序号 | <维度名> | [单位：…] | [工资水平|分位值] | 10% 25% 50% 75% 90%
#   then data rows: <序号> <名称(可折行,可带脚注标记)> <5个数值>

PCT5 = ["10%", "25%", "50%", "75%", "90%"]
SEQ_RE = re.compile(r"^\d{1,3}$")
BIGNUM_RE = re.compile(r"^\d{4,9}$|^\d{1,3}(,\d{3})+$")
HEADER_SKIP = ("工资水平", "分位值")
SEQ_STOP = ("序号", "序", "号")


def tokenize(text):
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def is_bignum(tok):
    return bool(BIGNUM_RE.match(tok.replace("，", ",")))


def to_int(tok):
    return int(tok.replace(",", "").replace("，", ""))


def find_page(doc, marker, start=0, end=None):
    """First page index >= start whose text contains marker."""
    for i in range(start, end if end is not None else len(doc)):
        if marker in doc[i].get_text():
            return i
    return None


def _header_dim(tokens, pct_idx):
    """Dimension name = tokens between 序号-fragment run and the 10%..90% run."""
    parts = []
    j = pct_idx - 1
    while j >= 0 and len(parts) <= 4:
        tok = tokens[j]
        if tok in SEQ_STOP:
            break
        if tok.startswith("单位") or tok in HEADER_SKIP:
            j -= 1
            continue
        parts.insert(0, tok)
        j -= 1
    return "".join(parts)


def parse_page_rows(text, dim_filter):
    """Parse all percentile tables on one page whose dimension matches.

    Only rows belonging to a header whose dimension equals dim_filter (or
    every percentile table when dim_filter is None) are returned. Rows after
    a non-matching header are skipped until the next matching header.
    Returns list of dicts {seq, name, vals[p10,p25,p50,p75,p90]}.
    """
    tokens = tokenize(text)
    rows = []
    i = 0
    last_seq = 0
    active = dim_filter is None
    while i < len(tokens):
        if tokens[i: i + 5] == PCT5:
            dim = _header_dim(tokens, i)
            i += 5
            active = dim_filter is None or dim == dim_filter
            last_seq = 0
            continue
        if active and SEQ_RE.match(tokens[i]):
            seq = int(tokens[i])
            j = i + 1
            name_parts = []
            while j < len(tokens) and not is_bignum(tokens[j]) and j - i <= 8:
                name_parts.append(tokens[j])
                j += 1
            if (name_parts and j + 5 <= len(tokens)
                    and all(is_bignum(tokens[k]) for k in range(j, j + 5))
                    and (seq > last_seq or seq == 1)):
                vals = [to_int(tokens[k]) for k in range(j, j + 5)]
                rows.append({"seq": seq, "name": clean_name(name_parts),
                             "vals": vals})
                last_seq = seq
                i = j + 5
                continue
        i += 1
    return rows


def clean_name(parts):
    name = "".join(parts)
    name = re.sub(r"\s+", "", name)
    # strip trailing footnote markers like '...人员）1' / '...人员S2'
    if len(name) > 6:
        name = re.sub(r"(?:S?\d{1,2})+$", "", name)
    return name


def parse_section(doc, start_page, end_page, start_marker, end_marker, dim):
    """Parse pages [start_page..end_page] keeping only dim tables.

    On the boundary pages the text is truncated at the marker position so a
    neighbouring section sharing the same dimension cannot leak in
    (start_marker: keep text AFTER it; end_marker: keep text BEFORE it).
    """
    rows = []
    for page in range(start_page, end_page + 1):
        text = doc[page].get_text()
        if page == start_page and start_marker:
            pos = text.find(start_marker)
            if pos >= 0:
                text = text[pos:]
        if page == end_page and end_marker:
            pos = text.find(end_marker)
            if pos >= 0:
                text = text[:pos]
        rows.extend(parse_page_rows(text, dim))
    return rows


# ---------------------------------------------------------------------------
# education x tenure handling (深圳 分学历与工龄)
# ---------------------------------------------------------------------------

TENURE_RE = re.compile(
    r"^(1（含）年以下|2～3年|4～5年|6～10年|11年以上)$")
TENURE_MAP = {
    "1（含）年以下": "1年以下",
    "2～3年": "2-3年",
    "4～5年": "4-5年",
    "6～10年": "6-10年",
    "11年以上": "11年以上",
}


def education_tenure_records(rows, city, year, source, source_url, category):
    """学历行 -> position=学历, exp=不限; 工龄行 -> position=所属学历, exp=工龄."""
    records = []
    current_edu = None
    for row in rows:
        name = re.sub(r"\s+", "", row["name"])
        p10, _p25, p50, _p75, p90 = row["vals"]
        if TENURE_RE.match(name):
            if current_edu:
                records.append(make_record(
                    current_edu, city, TENURE_MAP[name], p10, p50, p90,
                    year, source, source_url, category))
        else:
            current_edu = name
            records.append(make_record(
                name, city, "不限", p10, p50, p90,
                year, source, source_url, category))
    return records


# ---------------------------------------------------------------------------
# record assembly
# ---------------------------------------------------------------------------

def make_record(position, city, experience_level, salary_min, salary_median,
                salary_max, year, source, source_url, category):
    return {
        "position": position,
        "city": city,
        "experience_level": experience_level,
        "salary_min": int(salary_min),
        "salary_median": int(salary_median),
        "salary_max": int(salary_max),
        "year": int(year),
        "source": source,
        "source_url": source_url,
        "category": category,
        "unit": "元/年",
    }


def position_records(rows, city, year, source, source_url, category):
    records = []
    seen_names = set()
    for row in rows:
        name = row["name"]
        if not name or name in seen_names:
            continue
        p10, _p25, p50, _p75, p90 = row["vals"]
        seen_names.add(name)
        records.append(make_record(
            name, city, "不限", p10, p50, p90,
            year, source, source_url, category))
    return records


# ---------------------------------------------------------------------------
# city scrapers
# ---------------------------------------------------------------------------

SOURCES = [
    {
        "key": "gz",
        "city": "广州市",
        "page_url": "https://rsj.gz.gov.cn/zwdt/tzgg/content/post_10619688.html",
        "pdf_fallback": "https://rsj.gz.gov.cn/attachment/7/7952/7952736/10619688.pdf",
        "pdf_cache": "gz_2025.pdf",
        "year": 2024,  # 前言: 调查时期指标为2024年1月1日至12月31日
        "source": "广州市人社局《2025年人力资源市场工资价位》",
        "sections": [
            {  # （一）分职业工资价位, 印刷页17-33
                "start_marker": "（一）分职业工资价位",
                "end_marker": "（二）分行业不同职业工资价位",
                "search_from": 15,
                "dim": "职业",
                "category": "分职业工资价位",
                "mode": "position",
            },
            {  # 四、“羊城家政”工资价位 -> (一)分职业, 印刷页91
                "start_marker": "四、“羊城家政”工资价位",
                "end_marker": "第三部分",
                "search_from": 90,
                "dim": "职业",
                "category": "羊城家政分职业工资价位",
                "mode": "position",
            },
        ],
    },
    {
        "key": "sz",
        "city": "深圳市",
        "page_url": "https://hrss.sz.gov.cn/xxgk/tjsj/zxtj/content/post_12735120.html",
        "pdf_fallback": "https://hrss.sz.gov.cn/attachment/1/1703/1703629/12735120.pdf",
        "pdf_cache": "sz_2025.pdf",
        "year": 2024,  # 编制说明: 调查的时期指标为2024年1月1日至12月31日
        "source": "深圳市人社局《2025年人力资源市场工资价位》",
        "sections": [
            {  # 整体工资价位（四）分学历与工龄 (学历x工龄)
                "start_marker": "（四）分学历与工龄的工资价位",
                "end_marker": "（五）分职业细类的工资价位",
                "search_from": 8,
                "dim": "学历-工龄",
                "category": "分学历与工龄工资价位",
                "mode": "education_tenure",
            },
            {  # （五）分职业细类的工资价位 (整体部分, 不含分行业重复)
                "start_marker": "（五）分职业细类的工资价位",
                "end_marker": "二、行业工资价位",
                "search_from": 8,
                "dim": "职业",
                "category": "分职业细类工资价位",
                "mode": "position",
            },
        ],
    },
    {
        "key": "hz",
        "city": "杭州市",
        "page_url": None,  # 公告以官方PDF形式发布于浙江政务网附件域
        "pdf_fallback": ("https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a."
                         "internet.cloud.zj.gov.cn/jcms_files/jcms1/web3163/"
                         "site/attach/0/8de07211fbc54b69b37cb7c62f3ddc47.pdf"),
        "pdf_cache": "hz_2023.pdf",
        "year": 2023,
        "source": "杭州市人社局《2023年企业薪酬调查信息》",
        "sections": [
            {  # 一、不同职业小类企业从业人员工资价位(2023年), 全文仅此维度
                "start_marker": None,
                "end_marker": None,
                "search_from": 0,
                "dim": "职业小类",
                "category": "职业小类工资价位",
                "mode": "position",
            },
        ],
    },
]


def scrape_city(cfg):
    """Returns (records, status_report_entries)."""
    entries = []
    # 1) locate PDF url
    pdf_url = cfg["pdf_fallback"]
    if cfg["page_url"]:
        html = http_get(cfg["page_url"])
        links = find_pdf_links(html)
        if links:
            pdf_url = links[0]
            entries.append(f"公告页解析到附件: {pdf_url}")
        else:
            entries.append("公告页未发现附件链接, 使用备用URL")
    # 2) download (or reuse cache)
    pdf_path, how = download_pdf(pdf_url, cfg["pdf_cache"])
    entries.append(f"PDF {how}: {pdf_path}")
    # 3) parse sections
    doc = fitz.open(pdf_path)
    records = []
    for sec in cfg["sections"]:
        start = (find_page(doc, sec["start_marker"], sec["search_from"])
                 if sec["start_marker"] else sec["search_from"])
        if start is None:
            entries.append(f"[{sec['category']}] 起始标记未找到: "
                           f"{sec['start_marker']} -> 跳过")
            continue
        if sec["end_marker"]:
            end = find_page(doc, sec["end_marker"], start + 1)
            if end is None:  # end marker on the start page itself
                end = start if sec["end_marker"] in doc[start].get_text() \
                    else len(doc) - 1
        else:
            end = min(start + 40, len(doc) - 1)
        rows = parse_section(doc, start, end, sec["start_marker"],
                             sec["end_marker"], sec["dim"])
        if sec["mode"] == "education_tenure":
            recs = education_tenure_records(
                rows, cfg["city"], cfg["year"], cfg["source"],
                cfg["page_url"] or pdf_url, sec["category"])
        else:
            recs = position_records(
                rows, cfg["city"], cfg["year"], cfg["source"],
                cfg["page_url"] or pdf_url, sec["category"])
        entries.append(f"[{sec['category']}] pages {start}-{end} "
                       f"dim={sec['dim']} rows={len(rows)} -> {len(recs)}条")
        records.extend(recs)
    doc.close()
    return records, entries


# ---------------------------------------------------------------------------
# verification against manually-read公告原文 (spot checks)
# ---------------------------------------------------------------------------

SPOT_CHECKS = [
    # (city, position, experience_level, field, expected)  values read from PDF
    ("深圳市", "大学本科", "不限", "salary_median", 157508),
    ("深圳市", "硕士研究生", "不限", "salary_median", 263400),
    ("深圳市", "大学本科", "2-3年", "salary_median", 112233),
    ("广州市", "财务部门经理", "不限", "salary_median", 126122),
    ("广州市", "单位负责人", "不限", "salary_min", 59000),
    ("杭州市", "会计专业人员", "不限", "salary_median", 97770),
]


def verify(records):
    problems = []
    for r in records:
        if not (0 < r["salary_min"] <= r["salary_median"] <= r["salary_max"]):
            problems.append(f"percentile order violated: {r}")
    for city, pos, exp, field, expected in SPOT_CHECKS:
        hit = next((r for r in records if r["city"] == city
                    and r["position"] == pos
                    and r["experience_level"] == exp), None)
        if hit is None:
            problems.append(f"spot-check miss: {city}/{pos}/{exp}")
        elif hit[field] != expected:
            problems.append(
                f"spot-check mismatch {city}/{pos}/{exp} {field}: "
                f"got {hit[field]}, expected {expected} (公告原文)")
    return problems


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def run():
    all_records = []
    report = []
    for cfg in SOURCES:
        name = f"{cfg['city']} {cfg['source']}"
        try:
            recs, entries = scrape_city(cfg)
            report.append((name, "OK" if recs else "EMPTY", len(recs)))
            for e in entries:
                report.append((f"    {cfg['city']}", e, ""))
            all_records.extend(recs)
        except HTTPBlockedError as exc:
            report.append((name, f"BLOCKED-ABANDONED: {exc}", 0))
        except Exception as exc:  # noqa: BLE001
            report.append((name, f"FAILED: {type(exc).__name__}: {exc}", 0))

    seen, unique = set(), []
    for r in all_records:
        key = (r["city"], r["position"], r["experience_level"],
               r["category"], r["year"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(unique, fh, ensure_ascii=False, indent=2)

    print("=" * 76)
    for name, status, n in report:
        if isinstance(n, int):
            print(f"[{status:<8}] {n:>4}条  {name}")
        else:
            print(f"    {name} {status}")
    print("=" * 76)
    by_city = {}
    for r in unique:
        by_city.setdefault(r["city"], {"n": 0, "cats": {}})
        by_city[r["city"]]["n"] += 1
        cat = r["category"]
        by_city[r["city"]]["cats"][cat] = by_city[r["city"]]["cats"].get(cat, 0) + 1
    for city, info in sorted(by_city.items()):
        cats = ", ".join(f"{k}:{v}" for k, v in sorted(info["cats"].items()))
        print(f"  {city}: {info['n']}条  ({cats})")
    exp_levels = sorted({r["experience_level"] for r in unique})
    print(f"  experience_levels: {exp_levels}")
    print(f"  total unique records: {len(unique)}")
    print(f"  output: {OUTPUT_FILE}")
    print("\nrobots status:")
    for origin, note in ROBOTS_NOTES.items():
        if origin.startswith("note-"):
            print(f"  [note] {note}")
        else:
            print(f"  {origin}: {note}")
    problems = verify(unique)
    if problems:
        print("\nVERIFICATION PROBLEMS:")
        for p in problems:
            print(f"  ! {p}")
    else:
        print("\nspot-check vs 公告原文: all passed "
              f"({len(SPOT_CHECKS)} checks, percentile order OK)")
    ok = (len(unique) >= 60 and len(by_city) >= 2 and not problems)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
