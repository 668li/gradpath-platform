# -*- coding: utf-8 -*-
"""Position-granularity salary benchmark EXPANSION scraper for GradPath.

Extends salary_position_scraper.py (existing 1046 records for 广州/深圳/杭州)
with 4 more city-level 人社局 announcements. All sources are PUBLIC government
pages / official attachments; every record carries source_url and values are
copied verbatim from the announcement (万元/年 tables are unit-converted to
元/年 by x10000, noted per-source below).

New sources (all verified during research, robots.txt checked at runtime):
  1. 重庆市人社局《重庆市2024年度人力资源市场工资价位和企业人工成本信息》
     - 公告页: https://rlsbj.cq.gov.cn/zwxx_182/tzgg/202508/t20250801_14865923.html
     - INLINE HTML tables: 分职业中类 (64 职业) + 分岗位等级, 单位 元/年, 2024年
     - robots.txt: HTTP 403 (non-standard; no Disallow readable). Per repo
       convention (salary_position_scraper.check_robots) the public document
       itself is fetched once and its response decides; content HTTP 200.
  2. 济南市人社局《关于发布2024年人力资源市场工资价位的通知》
     - 公告页: http://jnhrss.jinan.gov.cn/col18578/art/2025/art_18578_4814322.html
     - 附件 docx (from the announcement page): 分职业小类 (149) + 分数字职业
       + 分岗位等级, 单位 万元/年 -> x10000 => 元/年, 表题标注 2024年
     - robots.txt: HTTP 200 but serves an HTML page (no robots rules) -> no
       matching Disallow
  3. 武汉市人社局《武汉市2022年企业薪酬调查信息》
     - 公告页: https://rsj.wuhan.gov.cn/zwgk_17/fdzdgknr/sjfb/2023_48053/202311/t20231103_2293938.html
     - INLINE HTML tables: 分职业 (167 职业) + 分岗位等级, 单位 元/年, 2022年
     - robots.txt: HTTP 404 => unrestricted
  4. 东莞市人社局《2024年东莞市人力资源市场工资价位》(调查时期指标为
     2023-01-01 至 2023-12-31 => data year 2023)
     - 公告页: http://dghrss.dg.gov.cn/xwzx/gsgg/tzgg/content/post_4309852.html
     - 附件 PDF: 分学历工资价位 (5 学历级 x 5 分位) + 分岗位类型 (17) +
       分职业 (~130), 单位 万元/年 -> x10000 => 元/年
     - robots.txt: HTTP 404 => unrestricted

Abandoned sources (honest record, 未绕过):
  - 成都市 (锦江区政府转发页): HTTP 412 Precondition Failed on content ->
    abandoned (未在原始 cdhrss 域上定位到可解析明细页)
  - 湖北省人社厅 2024 企业薪酬调查信息页: 页面无内嵌分位数表、无附件 -> 无可解析数据
  - 西安市: 未检索到公开分职业分位数公告页
  - yz.chsi.com.cn (研招网) / 任何登录内容: 未触碰

Compliance (mirrors salary_position_scraper.py):
  - robots.txt checked per host (404 => unrestricted; Disallow match => skip;
    403 on robots endpoint itself => recorded, content response decides)
  - 403/418/429 on content => HTTPBlockedError, source abandoned, no bypass
  - 1.5s polite delay between HTTP requests, identified crawler UA
  - every record carries source_url; values copied verbatim from 公告原文
    (percentile mapping 10% -> salary_min, 50% -> salary_median, 90% ->
    salary_max; 万元/年 sources unit-converted x10000 to 元/年)

Output: salary_position_expand.json (same directory), deduplicated against
the existing salary_position_data.json on (position, city, year).

Run:  py -3.13 salary_position_expand.py
"""
import html as html_mod
import json
import os
import re
import sys
import time
import urllib.parse
import zipfile
from urllib.parse import urlsplit, urljoin

import requests

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF (fitz) required: py -3.13 -m pip install pymupdf") from exc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "salary_position_expand.json")
EXISTING_FILE = os.path.join(BASE_DIR, "salary_position_data.json")
PDF_CACHE_DIR = os.path.join(BASE_DIR, "pdf_cache")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
REQUEST_TIMEOUT = 40
POLITE_DELAY = 1.5  # seconds between HTTP requests

BLOCKING_STATUSES = (403, 418, 429)


class HTTPBlockedError(RuntimeError):
    """Raised on 403/418/429 — source must be abandoned, never bypassed."""


# ---------------------------------------------------------------------------
# HTTP layer (robots-aware, rate-limited) — mirrors salary_position_scraper
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


def check_robots(url):
    """Return (allowed, note). 404 => unrestricted (per repo convention)."""
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        _politeness_wait(robots_url)
        resp = requests.get(robots_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            return True, "no robots.txt (404) -> unrestricted"
        if resp.status_code in BLOCKING_STATUSES:
            # robots endpoint itself blocked; be conservative but do not
            # auto-bypass: attempt the public document once, content decides.
            return True, f"robots.txt HTTP {resp.status_code} (non-standard)"
        if resp.status_code == 200:
            path = parts.path or "/"
            for line in resp.text.splitlines():
                m = re.match(r"(?i)disallow\s*:\s*(\S*)", line.strip())
                if m and m.group(1) and path.startswith(m.group(1)):
                    return False, f"robots.txt Disallow {m.group(1)} matches path"
            if "<html" in resp.text[:2000].lower():
                return True, "robots.txt 200 but serves HTML (no rules) -> allowed"
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
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        # network hiccup (NOT a block): one polite retry after the usual delay
        _politeness_wait(url)
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    if resp.status_code in BLOCKING_STATUSES:
        raise HTTPBlockedError(f"HTTP {resp.status_code} for {url} -> abandoned")
    resp.raise_for_status()
    if binary:
        return resp.content
    if resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "ascii"):
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


# ---------------------------------------------------------------------------
# generic row model: texts + 5 percentile numbers, ascending-checked
# ---------------------------------------------------------------------------

NUM_RE = re.compile(r"^\d{1,9}(?:\.\d{1,2})?$")
SEQ_RE = re.compile(r"^\d{1,3}$")
GROUP_WORDS = {"管理类", "专业技术类", "职业技能类", "技能类", "技术类"}
PCT5 = ["10%", "25%", "50%", "75%", "90%"]


def to_yuan(tok, wan):
    v = float(tok.replace(",", "").replace("，", ""))
    return int(round(v * 10000)) if wan else int(round(v))


def clean_name(name):
    name = re.sub(r"\s+", "", name)
    # strip trailing footnote/flag markers: '*', 'L/S', 'S', 'L' (绿色/数字职业标)
    name = re.sub(r"(?:L/S|[LS])+$", "", name) if re.search(r"[A-Z/*]$", name) else name
    name = name.rstrip("*")
    return name


def row_from_cells(cells, wan):
    """cells -> {name, vals} or None.

    A data row has >=5 trailing numbers (10/25/50/75/90 percentiles, strictly
    ascending) plus at least one text cell. Leading pure 1-3 digit sequence
    numbers are ignored. Group words (管理类/…) are dropped for grade tables;
    for occupation tables all remaining text cells join into the name.
    """
    cells = [c for c in cells if c != ""]
    if not cells:
        return None
    texts, nums = [], []
    for c in cells:
        (nums if NUM_RE.match(c) else texts).append(c)
    if len(nums) < 5:
        return None
    vals_tok = nums[-5:]
    vals = [to_yuan(t, wan) for t in vals_tok]
    # non-strict: some announcements publish equal neighbouring percentiles
    # after rounding (e.g. 济南 消防和应急救援人员 50%=75%=7.90万元/年)
    if not all(vals[i] <= vals[i + 1] for i in range(4)):
        return None
    # drop leading sequence numbers mixed into texts (e.g. rows without cell
    # borders): pure 1-3 digit cells that appear before any real text
    texts = [t for t in texts if not (SEQ_RE.match(t) and len(t) <= 3)]
    texts = [t for t in texts if t not in GROUP_WORDS]
    if not texts:
        return None
    return {"name": clean_name("".join(texts)), "vals": vals}


def make_record(position, city, salary_min, salary_median, salary_max, year,
                source, source_url, category):
    return {
        "position": position,
        "city": city,
        "experience_level": "不限",
        "salary_min": int(salary_min),
        "salary_median": int(salary_median),
        "salary_max": int(salary_max),
        "year": int(year),
        "source": source,
        "source_url": source_url,
        "category": category,
        "unit": "元/年",
    }


def rows_to_records(rows, city, year, source, source_url, category, entries,
                    tag):
    records, seen = [], set()
    for row in rows:
        name = row["name"]
        if not name or name in seen or name in ("分位值", "序号"):
            continue
        seen.add(name)
        p10, _p25, p50, _p75, p90 = row["vals"]
        records.append(make_record(name, city, p10, p50, p90, year, source,
                                   source_url, category))
    entries.append(f"[{tag}] parsed rows={len(rows)} -> {len(records)}条")
    return records


# ---------------------------------------------------------------------------
# source 1+3: inline HTML tables (重庆 / 武汉)
# ---------------------------------------------------------------------------

def html_tables(html):
    out = []
    for tbl in re.findall(r"<table[^>]*>.*?</table>", html, re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S | re.I):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)
            cells = [re.sub(r"\s+", "", html_mod.unescape(
                re.sub(r"<[^>]+>", "", c))) for c in cells]
            rows.append(cells)
        out.append(rows)
    return out


def scrape_html_tables(cfg):
    entries = []
    page_html = http_get(cfg["page_url"])
    tables = html_tables(page_html)
    entries.append(f"公告页获取成功, 内嵌表格数={len(tables)}")
    records = []
    for sec in cfg["sections"]:
        dim = sec["dim"]
        # locate table whose header row mentions the dimension column
        target = None
        for rows in tables:
            head = [c for row in rows[:3] for c in row]
            if any(dim in h for h in head):
                target = rows
                break
        if target is None:
            entries.append(f"[{sec['category']}] 未找到维度 {dim} 的表格 -> 跳过")
            continue
        rows = [row_from_cells(r, cfg["wan_unit"]) for r in target]
        rows = [r for r in rows if r]
        records.extend(rows_to_records(
            rows, cfg["city"], cfg["year"], cfg["source"], cfg["page_url"],
            sec["category"], entries, sec["category"]))
    return records, entries


# ---------------------------------------------------------------------------
# source 2: docx attachment (济南, 万元/年)
# ---------------------------------------------------------------------------

def docx_tables(data):
    xml = zipfile.ZipFile(__import__("io").BytesIO(data)).read(
        "word/document.xml").decode("utf-8")
    out = []
    for tbl in re.findall(r"<w:tbl>.*?</w:tbl>", xml, re.S):
        rows = []
        for tr in re.findall(r"<w:tr[ >].*?</w:tr>", tbl, re.S):
            cells = []
            for tc in re.findall(r"<w:tc>.*?</w:tc>", tr, re.S):
                txt = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc))
                cells.append(re.sub(r"\s+", "", html_mod.unescape(txt)))
            rows.append(cells)
        out.append(rows)
    return out


def scrape_docx(cfg):
    entries = []
    page_html = http_get(cfg["page_url"])
    links = sorted(set(re.findall(r'href="([^"]+\.docx[^"]*)"', page_html, re.I)))
    if not links:
        raise RuntimeError("公告页未找到 docx 附件")
    docx_url = urljoin(cfg["page_url"], links[0])
    entries.append(f"公告页解析到附件: {docx_url}")
    data = http_get(docx_url, binary=True)
    cache = os.path.join(PDF_CACHE_DIR, cfg["cache_name"])
    os.makedirs(PDF_CACHE_DIR, exist_ok=True)
    with open(cache, "wb") as fh:
        fh.write(data)
    tables = docx_tables(data)
    entries.append(f"docx 下载 {len(data)} bytes, 表格数={len(tables)}")
    records = []
    for sec in cfg["sections"]:
        dim = sec["dim"]
        occurrence = sec.get("occurrence", 0)
        seen = 0
        target = None
        for rows in tables:
            head = [c for row in rows[:3] for c in row]
            if any(dim in h for h in head):
                if seen == occurrence:
                    target = rows
                    break
                seen += 1
        if target is None:
            entries.append(f"[{sec['category']}] 未找到第{occurrence + 1}个维度 "
                           f"{dim} 表格 -> 跳过")
            continue
        rows = [row_from_cells(r, cfg["wan_unit"]) for r in target]
        rows = [r for r in rows if r]
        records.extend(rows_to_records(
            rows, cfg["city"], cfg["year"], cfg["source"], cfg["page_url"],
            sec["category"], entries, sec["category"]))
    return records, entries


# ---------------------------------------------------------------------------
# source 4: announcement PDF with token-stream tables (东莞, 万元/年)
# Layout: 序|号|<dim>|工资水平（万元/年）|10%|25%|50%|75%|90% then data rows;
# names may wrap across two lines; values carry decimals (万元).
# ---------------------------------------------------------------------------

def tokenize(text):
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def find_page(doc, marker, start=0, end=None):
    for i in range(start, end if end is not None else len(doc)):
        if marker in doc[i].get_text().replace(" ", ""):
            return i
    return None


def parse_pdf_page_rows(text, wan):
    tokens = tokenize(text)
    rows = []
    i = 0
    while i < len(tokens):
        if tokens[i: i + 5] == PCT5:
            i += 5
            # collect name tokens until 5 consecutive numbers
            j = i
            while j < len(tokens):
                seq_m = SEQ_RE.match(tokens[j])
                k = j + 1 if seq_m else j
                name_parts = []
                while k < len(tokens) and not NUM_RE.match(tokens[k]) \
                        and len(name_parts) <= 6:
                    name_parts.append(tokens[k])
                    k += 1
                if (name_parts and k + 5 <= len(tokens)
                        and all(NUM_RE.match(tokens[m]) for m in range(k, k + 5))
                        and k - (j + 1 if seq_m else j) <= 7):
                    vals = [to_yuan(tokens[m], wan) for m in range(k, k + 5)]
                    if all(vals[n] <= vals[n + 1] for n in range(4)):
                        name = clean_name("".join(name_parts))
                        if name and name not in ("序号", "分位值", "工资水平（万元/年）"):
                            rows.append({"name": name, "vals": vals})
                            j = k + 5
                            continue
                break
            i = j if j > i else i + 5
        else:
            i += 1
    return rows


def _cut_at_marker(text, marker):
    """Truncate page text BEFORE the line containing marker (line-level,
    whitespace-normalized so wrapped headings still match)."""
    lines = text.splitlines()
    marker_norm = marker.replace(" ", "").replace("\u3000", "")
    for idx, ln in enumerate(lines):
        if marker_norm in ln.replace(" ", "").replace("\u3000", ""):
            return "\n".join(lines[:idx])
    return text


def _cut_after_marker(text, marker):
    """Keep only lines AFTER the line containing marker (drops the previous
    section's table when two sections share one PDF page)."""
    lines = text.splitlines()
    marker_norm = marker.replace(" ", "").replace("\u3000", "")
    for idx, ln in enumerate(lines):
        if marker_norm in ln.replace(" ", "").replace("\u3000", ""):
            return "\n".join(lines[idx + 1:])
    return text


def scrape_pdf(cfg):
    entries = []
    page_html = http_get(cfg["page_url"])
    links = sorted(set(re.findall(r'href="([^"]+\.pdf[^"]*)"', page_html, re.I)))
    pdf_url = urljoin(cfg["page_url"], links[0]) if links else cfg["pdf_fallback"]
    entries.append(f"PDF 附件: {pdf_url}")
    cache = os.path.join(PDF_CACHE_DIR, cfg["cache_name"])
    os.makedirs(PDF_CACHE_DIR, exist_ok=True)
    if not (os.path.exists(cache) and os.path.getsize(cache) > 1024):
        with open(cache, "wb") as fh:
            fh.write(http_get(pdf_url, binary=True))
        entries.append(f"PDF downloaded -> {cache}")
    else:
        entries.append(f"PDF cached -> {cache}")
    doc = fitz.open(cache)
    records = []
    for sec in cfg["sections"]:
        start = find_page(doc, sec["start_marker"], sec.get("search_from", 0))
        if start is None:
            entries.append(f"[{sec['category']}] 起始标记未找到 -> 跳过")
            continue
        # search end marker starting AT the start page (section may share it)
        if sec["end_marker"]:
            end = find_page(doc, sec["end_marker"], start)
            if end is None:
                end = len(doc) - 1
        else:
            end = min(start + 12, len(doc) - 1)
        rows = []
        for page in range(start, end + 1):
            text = doc[page].get_text()
            if page == start and sec["start_marker"]:
                text = _cut_after_marker(text, sec["start_marker"])
            if page == end and sec["end_marker"]:
                text = _cut_at_marker(text, sec["end_marker"])
            rows.extend(parse_pdf_page_rows(text, cfg["wan_unit"]))
        entries.append(f"[{sec['category']}] pages {start}-{end} rows_raw={len(rows)}")
        records.extend(rows_to_records(
            rows, cfg["city"], cfg["year"], cfg["source"], cfg["page_url"],
            sec["category"], entries, sec["category"]))
    doc.close()
    return records, entries


# ---------------------------------------------------------------------------
# source configs
# ---------------------------------------------------------------------------

SOURCES = [
    {
        "key": "cq",
        "city": "重庆市",
        "kind": "html",
        "page_url": "https://rlsbj.cq.gov.cn/zwxx_182/tzgg/202508/t20250801_14865923.html",
        "year": 2024,  # 表题: 重庆市分职业中类企业从业人员工资价位（2024年）
        "wan_unit": False,  # 单位: 元/年
        "source": "重庆市人社局《2024年度人力资源市场工资价位和企业人工成本信息》",
        "sections": [
            {"dim": "职业中类名称", "category": "分职业中类工资价位"},
            {"dim": "岗位等级", "category": "分岗位等级工资价位"},
        ],
    },
    {
        "key": "jn",
        "city": "济南市",
        "kind": "docx",
        "page_url": "http://jnhrss.jinan.gov.cn/col18578/art/2025/art_18578_4814322.html",
        "year": 2024,  # 表题: 分职业小类企业从业人员工资价位（2024年）
        "wan_unit": True,  # 单位: 万元/年 -> x10000 => 元/年
        "cache_name": "jn_2024.docx",
        "source": "济南市人社局《2024年人力资源市场工资价位》",
        "sections": [
            {"dim": "职业", "occurrence": 0, "category": "分职业小类工资价位"},
            {"dim": "职业", "occurrence": 1, "category": "分数字职业工资价位"},
            {"dim": "岗位等级", "occurrence": 0, "category": "分岗位等级工资价位"},
        ],
    },
    {
        "key": "wh",
        "city": "武汉市",
        "kind": "html",
        "page_url": "https://rsj.wuhan.gov.cn/zwgk_17/fdzdgknr/sjfb/2023_48053/202311/t20231103_2293938.html",
        "year": 2022,  # 表题: 武汉市分职业企业从业人员工资价位（2022年）
        "wan_unit": False,  # 单位: 元/年
        "source": "武汉市人社局《武汉市2022年企业薪酬调查信息》",
        "sections": [
            {"dim": "职业名称", "category": "分职业工资价位"},
            {"dim": "岗位等级", "category": "分岗位等级工资价位"},
        ],
    },
    {
        "key": "dg",
        "city": "东莞市",
        "kind": "pdf",
        "page_url": "http://dghrss.dg.gov.cn/xwzx/gsgg/tzgg/content/post_4309852.html",
        "pdf_fallback": "http://dghrss.dg.gov.cn/attachment/0/304/304846/4309852.pdf",
        "cache_name": "dg_2024.pdf",
        "year": 2023,  # 编制说明: 调查时期指标为2023年1月1日至12月31日
        "wan_unit": True,  # 单位: 万元/年 -> x10000 => 元/年
        "source": "东莞市人社局《2024年东莞市人力资源市场工资价位》",
        "sections": [
            {"start_marker": "（三）分学历工资价位",
             "end_marker": "（四）分岗位类型工资价位",
             "search_from": 5, "category": "分学历工资价位"},
            {"start_marker": "（四）分岗位类型工资价位",
             "end_marker": "二、从业人员职业工资价位",
             "search_from": 5, "category": "分岗位类型工资价位"},
            {"start_marker": "（一）分职业工资价位",
             "end_marker": "（二）制造业职业工资价位",
             "search_from": 5, "category": "分职业工资价位"},
        ],
    },
]


SCRAPERS = {"html": scrape_html_tables, "docx": scrape_docx, "pdf": scrape_pdf}


# ---------------------------------------------------------------------------
# verification against manually-read 公告原文 (spot checks, >=2 per source)
# ---------------------------------------------------------------------------

SPOT_CHECKS = [
    # (city, position, field, expected)  values read from the announcements
    ("重庆市", "企业单位负责人", "salary_median", 93793),      # 52000/67117/93793/140000/228249
    ("重庆市", "其他生产制造及有关人员", "salary_min", 37412),
    ("重庆市", "高层管理岗", "salary_median", 101754),
    ("济南市", "企业负责人", "salary_median", 151300),         # 15.13万元/年 x10000
    ("济南市", "自然科学和地球科学研究人员", "salary_min", 60200),  # 6.02万元/年
    ("济南市", "大地测量工程技术人员", "salary_max", 269800),  # 26.98万元/年 (L/S标记已清)
    ("济南市", "高层管理岗", "salary_median", 179200),         # 17.92万元/年
    ("武汉市", "企业董事", "salary_median", 103000),
    ("武汉市", "企业经理", "salary_min", 50926),
    ("武汉市", "安全员", "salary_max", 102714),
    ("武汉市", "高层管理岗", "salary_min", 58500),
    ("东莞市", "研究生（含博士、硕士）", "salary_median", 204000),  # 20.40万元/年
    ("东莞市", "大学本科", "salary_min", 52600),              # 5.26万元/年
    ("东莞市", "材料成形与改性工程技术人员", "salary_median", 79000),  # 7.90万元/年
    ("东莞市", "高级技师", "salary_median", 76300),           # 7.63万元/年
]


def verify(records):
    problems = []
    for r in records:
        if not (0 < r["salary_min"] <= r["salary_median"] <= r["salary_max"]):
            problems.append(f"percentile order violated: {r}")
    idx = {(r["city"], r["position"]): r for r in records}
    for city, pos, field, expected in SPOT_CHECKS:
        hit = idx.get((city, pos))
        if hit is None:
            problems.append(f"spot-check miss: {city}/{pos}")
        elif hit[field] != expected:
            problems.append(
                f"spot-check mismatch {city}/{pos} {field}: got {hit[field]}, "
                f"expected {expected} (公告原文)")
    return problems


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def run():
    all_records, report = [], []
    for cfg in SOURCES:
        name = f"{cfg['city']} {cfg['source']}"
        try:
            recs, entries = SCRAPERS[cfg["kind"]](cfg)
            report.append((name, "OK" if recs else "EMPTY", len(recs)))
            for e in entries:
                report.append((f"    {cfg['city']}", e, ""))
            all_records.extend(recs)
        except HTTPBlockedError as exc:
            report.append((name, f"BLOCKED-ABANDONED: {exc}", 0))
        except Exception as exc:  # noqa: BLE001
            report.append((name, f"FAILED: {type(exc).__name__}: {exc}", 0))

    # internal dedup
    seen, unique = set(), []
    for r in all_records:
        key = (r["city"], r["position"], r["experience_level"],
               r["category"], r["year"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # dedup against existing salary_position_data.json on (position, city, year)
    existing_keys = set()
    if os.path.exists(EXISTING_FILE):
        with open(EXISTING_FILE, encoding="utf-8") as fh:
            for r in json.load(fh):
                existing_keys.add((r["position"], r["city"], r["year"]))
    before = len(unique)
    unique = [r for r in unique
              if (r["position"], r["city"], r["year"]) not in existing_keys]
    dropped = before - len(unique)

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
    print(f"  dropped as duplicates of existing data: {dropped}")
    print(f"  total new unique records: {len(unique)}")
    print(f"  output: {OUTPUT_FILE}")
    print("\nrobots status:")
    for origin, note in ROBOTS_NOTES.items():
        print(f"  {origin}: {note}")
    problems = verify(unique)
    if problems:
        print("\nVERIFICATION PROBLEMS:")
        for p in problems:
            print(f"  ! {p}")
    else:
        print(f"\nspot-check vs 公告原文: all passed ({len(SPOT_CHECKS)} checks, "
              "percentile order OK)")
    ok = (len(unique) >= 200 and len(by_city) >= 3 and not problems)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
