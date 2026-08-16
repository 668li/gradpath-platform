# -*- coding: utf-8 -*-
"""Real government-published salary data scraper for GradPath.

Collects REAL, traceable salary statistics from public government sources:

  Source A (国家统计局 stats.gov.cn, 年度公告页):
    - 城镇单位就业人员年平均工资情况 (2023/2024/2025 数据公告)
    - 分 区域 / 行业 / 登记注册类别 / 岗位 average wages
    robots.txt: absent (HTTP 404) => crawling not restricted.

  Source B (上海市人社局 rsj.sh.gov.cn, 公开公告):
    - 2025年长三角一体化示范区制造业企业市场工资价位 (85 个职位 x 5 个分位数)
    - 2023年本市企业技能人才年平均工资 (2019-2023 序列等)
    robots.txt: absent (HTTP 404) => crawling not restricted.

  Not touched (compliance): yz.chsi.com.cn (研招网), login-walled content.
  data.stats.gov.cn easyquery API returned 403 (UrlACL) => abandoned per policy.
  cninfo (巨潮资讯) reachable but salary data only inside annual-report PDFs
  => out of scope this round (recorded in SOURCE_STATUS).

Output: salary_gov_data.json (same directory)
Record fields: {indicator, category, value, unit, region, industry, year,
                source, source_url, published_at}

Run:  py -3.13 salary_gov_scraper.py
"""
import json
import os
import re
import sys
import time

import requests

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salary_gov_data.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

REQUEST_TIMEOUT = 30
POLITE_DELAY = 2.0  # seconds between requests to the same host

SOURCE_STATUS = {}

NBS_PAGES = [
    # (data_year, url) — URL path encodes publish date /YYYYMM/tYYYYMMDD/
    (2025, "https://www.stats.gov.cn/sj/zxfb/202605/t20260515_1963707.html"),
    (2024, "https://www.stats.gov.cn/sj/zxfb/202505/t20250516_1959826.html"),
    (2023, "https://www.stats.gov.cn/sj/zxfb/202405/t20240520_1950434.html"),
]
NBS_SOURCE = "国家统计局"

SH_PAGES = [
    # (kind, url) kind: yrd_positions | skill_talent
    ("yrd_positions",
     "https://rsj.sh.gov.cn/tgzjw_17760/20251226/t0035_1437616.html"),
    ("skill_talent",
     "https://rsj.sh.gov.cn/tgzjw_17760/20241018/t0035_1428263.html"),
]
SH_SOURCE = "上海市人力资源和社会保障局"

JOB_LEVEL_COLS = [
    "中层及以上管理人员",
    "专业技术人员",
    "办事人员和有关人员",
    "社会生产服务和生活服务人员",
    "生产制造及有关人员",
]


# ----------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------

def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "ascii"):
        resp.encoding = "utf-8"
    return resp.text


def strip_tags(fragment):
    text = re.sub(r"<[^>]+>", "", fragment)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", "", text).strip()


def parse_tables(html):
    """Return list of tables; each table is a list of rows (list of cell texts).

    Single-cell caption rows such as '单位：元，%' are kept as table metadata
    position 0 is NOT guaranteed to be the header; use table_header() instead.
    """
    tables = []
    for tb in re.findall(r"<table[^>]*>.*?</table>", html, re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr[^>]*>.*?</tr>", tb, re.S | re.I):
            cells = [strip_tags(c) for c in
                     re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
            cells = [c for c in cells if c != ""]
            if cells:
                rows.append(cells)
        if len(rows) >= 2:
            tables.append(rows)
    return tables


UNIT_NOTE_RE = re.compile(r"^单位[：:]")


def drop_unit_notes(rows):
    """Drop leading caption rows like '单位：元，%' (single cell)."""
    return [r for r in rows if not (len(r) == 1 and UNIT_NOTE_RE.match(r[0]))]


def table_header(rows):
    """First row with >= 2 cells is the real header row."""
    for r in rows:
        if len(r) >= 2:
            return r
    return rows[0] if rows else []


def dedupe_tables(tables):
    """NBS pages embed a duplicated (mobile) copy of every table; drop repeats."""
    seen, out = set(), []
    for rows in tables:
        sig = "|".join("|".join(r) for r in rows)
        if sig not in seen:
            seen.add(sig)
            out.append(rows)
    return out


def to_number(text):
    m = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(m.group()) if m else None


def make_record(indicator, category, value, unit, region, industry, year,
                source, source_url, published_at):
    return {
        "indicator": indicator,
        "category": category,
        "value": value,
        "unit": unit,
        "region": region,
        "industry": industry,
        "year": year,
        "source": source,
        "source_url": source_url,
        "published_at": published_at,
    }


def check_robots(url):
    """Lightweight robots.txt awareness check (reporting only, non-blocking)."""
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        resp = requests.get(robots_url, headers=HEADERS, timeout=15)
        if resp.status_code == 404:
            return "no robots.txt (404) -> unrestricted"
        if resp.status_code == 200 and "disallow" in resp.text.lower():
            return "robots.txt present, review needed"
        return f"robots.txt HTTP {resp.status_code}, no Disallow observed"
    except Exception as exc:  # noqa: BLE001
        return f"robots check failed: {exc}"


# ----------------------------------------------------------------------------
# Source A: 国家统计局 annual average-wage announcements
# ----------------------------------------------------------------------------

def classify_nbs_table(rows):
    """Map a table to (dimension, unit_mode) by its header row."""
    rows = drop_unit_notes(rows)
    header = table_header(rows)
    if not header:
        return None, None
    joined = "".join("".join(r) for r in rows[:3])
    if "中层及以上管理人员" in joined:
        return "job_level", "single_year"
    if header and "区域" in header[0]:
        return "region", "two_year"
    if header and "行业" in header[0]:
        return "industry", "two_year"
    if header and "登记注册" in header[0]:
        return "registration_type", "two_year"
    return None, None


def section_of_heading(text):
    if "非私营" in text:
        return "城镇非私营单位"
    if "私营" in text and "非私营" not in text:
        return "城镇私营单位"
    if "规模以上" in text:
        return "规模以上企业"
    return None


def scrape_nbs_page(data_year, url):
    """Parse one NBS annual wage announcement into records."""
    html = fetch(url)
    m = re.search(r"/t(\d{4})(\d{2})(\d{2})_", url)
    published_at = (f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                    if m else f"{data_year}-01-01")
    records = []

    # Walk content in document order: remember the nearest preceding section
    # heading so each table is attributed to 非私营 / 私营 / 规上.
    tokens = re.split(r"(<table[^>]*>.*?</table>)", html, flags=re.S | re.I)
    section = None
    seen_sig = set()
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("<table"):
            if section is None:
                continue
            rows = parse_tables(tok)
            if not rows:
                continue
            rows = rows[0]
            sig = "|".join("|".join(r) for r in rows)
            if sig in seen_sig:  # skip duplicated mobile copy
                continue
            seen_sig.add(sig)
            dimension, mode = classify_nbs_table(rows)
            if dimension is None:
                continue
            records.extend(nbs_table_records(
                rows, dimension, mode, section, data_year,
                NBS_SOURCE, url, published_at))
        else:
            for head in re.findall(r">([^<>]*(?:一|二|三|四|五)、[^<>]{2,60})<", tok):
                sec = section_of_heading(head.strip())
                if sec:
                    section = sec
    return records


def nbs_table_records(rows, dimension, mode, section, data_year,
                      source, url, published_at):
    records = []
    indicator = f"{section}就业人员年平均工资"
    rows = drop_unit_notes(rows)
    if not rows:
        return records
    header = table_header(rows)
    dim_name = header[0] if header else ""
    data_rows = [r for r in rows if r is not header]

    if mode == "two_year":
        # header: <dim> | <yearN> | <yearN-1> | 名义增长率
        for row in data_rows:
            if len(row) < 2:
                continue
            name, v_cur = row[0], to_number(row[1])
            v_prev = to_number(row[2]) if len(row) > 2 else None
            if not name or v_cur is None:
                continue
            region = name if dimension == "region" and name != "合计" else None
            industry = name if dimension == "industry" and name != "合计" else None
            cat = {"region": "地区", "industry": "行业"}.get(dimension)
            if dimension == "registration_type":
                cat = f"登记注册类别-{name}"
            if name == "合计":
                cat = "全体"
            for year, val in ((data_year, v_cur), (data_year - 1, v_prev)):
                if val is not None:
                    records.append(make_record(
                        indicator, cat, val, "元/年", region, industry,
                        year, source, url, published_at))
    else:  # job_level: 规模以上企业按岗位
        # header rows: row0 [区域|行业|登记注册统计类别, 规模以上企业就业人员(merged)]
        #              row1 sub-columns [中层及以上管理人员, ...]
        cols = ["规模以上企业就业人员"] + JOB_LEVEL_COLS
        sub_idx = next((i for i, r in enumerate(rows) if "中层" in "".join(r)), -1)
        body = rows[sub_idx + 1:] if sub_idx >= 0 else data_rows
        for row in body:
            if not row:
                continue
            dim_value = row[0]
            region = dim_value if dim_name == "区域" and dim_value != "合计" else None
            industry = dim_value if dim_name == "行业" and dim_value != "合计" else None
            suffix = ""
            if dim_name == "登记注册统计类别" and dim_value != "合计":
                suffix = f"({dim_value})"
            for i, col in enumerate(cols):
                if i + 1 >= len(row):  # row[0] is the dimension name
                    break
                val = to_number(row[i + 1])
                if val is None:
                    continue
                records.append(make_record(
                    "规模以上企业就业人员年平均工资" if col == "规模以上企业就业人员"
                    else "规模以上企业分岗位就业人员年平均工资",
                    f"{col}{suffix}" if suffix else col,
                    val, "元/年", region, industry,
                    data_year, source, url, published_at))
    return records


# ----------------------------------------------------------------------------
# Source B1: 上海 长三角一体化示范区制造业企业市场工资价位 (position percentiles)
# ----------------------------------------------------------------------------

SH_PCT_COLS = ["90%分位数", "75%分位数", "50%分位数", "25%分位数", "10%分位数"]


def scrape_sh_yrd_positions(url):
    html = fetch(url)
    records = []
    published_m = re.search(r"发布时间[：:]\s*(\d{4}-\d{2}-\d{2})", html)
    published_at = published_m.group(1) if published_m else None
    for rows in dedupe_tables(parse_tables(html)):
        header = "".join(rows[0])
        if "分位数" not in header or "职位" not in header:
            continue
        for row in rows[1:]:
            if len(row) < 6 or not re.match(r"^\d+$", row[0]):
                continue
            position = row[1]
            for i, pct in enumerate(SH_PCT_COLS):
                val = to_number(row[2 + i])
                if val is None:
                    continue
                records.append(make_record(
                    "长三角一体化示范区制造业企业市场工资价位",
                    f"{position}({pct})", val, "元/年", "长三角一体化示范区",
                    "制造业", 2024, SH_SOURCE, url, published_at))
    return records


# ----------------------------------------------------------------------------
# Source B2: 上海 企业技能人才市场工资价位 (skilled-talent series)
# ----------------------------------------------------------------------------

def scrape_sh_skill_talent(url):
    html = fetch(url)
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    published_m = re.search(r"发布时间[：:]\s*(\d{4}-\d{2}-\d{2})", text)
    published_at = published_m.group(1) if published_m else None
    records = []

    # 2019—2023年，技能人才年平均工资分别为12.79、13.55、14.83、16.22和16.88万元。
    m = re.search(
        r"(\d{4})[—-](\d{4})年[，,]技能人才年平均工资分别为"
        r"([\d\.、和]+)万元", text)
    if m:
        start_year = int(m.group(1))
        vals = [to_number(v) for v in re.findall(r"[\d\.]+", m.group(3))]
        for offset, val in enumerate(vals):
            if val is not None:
                records.append(make_record(
                    "企业技能人才年平均工资", "技能人才合计", val * 10000,
                    "元/年", "上海市", None, start_year + offset,
                    SH_SOURCE, url, published_at))

    # “人工智能”产业高技能人才年工资高位数为33.08万元，增幅9.9%。 (3 industries)
    for ind, val in re.findall(
            r"[“\"]([\u4e00-\u9fa5]{2,12})[”\"]产业高技能人才年工资高位数为"
            r"([\d\.]+)万元", text):
        records.append(make_record(
            "高技能人才年工资高位数", f"{ind}产业", to_number(val) * 10000,
            "元/年", "上海市", f"{ind}", 2023, SH_SOURCE, url, published_at))

    # 高技能人才年工资中位数分别为18.91、18.67和17.76万元 (industries listed before)
    m = re.search(
        r"[“\"]制造业[”\"][“\"]交通运输、仓储和邮政业[”\"][“\"]信息传输、软件和信息技术服务业[”\"]"
        r"[，,]高技能人才年工资中位数分别为([\d\.、和]+)万元", text)
    if m:
        inds = ["制造业", "交通运输、仓储和邮政业", "信息传输、软件和信息技术服务业"]
        vals = [to_number(v) for v in re.findall(r"[\d\.]+", m.group(1))]
        for ind, val in zip(inds, vals):
            if val is not None:
                records.append(make_record(
                    "高技能人才年工资中位数", f"{ind}", val * 10000,
                    "元/年", "上海市", ind, 2023, SH_SOURCE, url, published_at))
    return records


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    all_records = []
    report = []

    def attempt(name, fn):
        try:
            recs = fn()
            report.append((name, "OK", len(recs)))
            return recs
        except Exception as exc:  # noqa: BLE001
            report.append((name, f"FAILED: {exc}", 0))
            return []

    for year, url in NBS_PAGES:
        time.sleep(POLITE_DELAY)
        all_records.extend(
            attempt(f"NBS-{year} {url}", lambda u=url, y=year:
                    scrape_nbs_page(y, u)))

    for kind, url in SH_PAGES:
        time.sleep(POLITE_DELAY)
        fn = (scrape_sh_yrd_positions if kind == "yrd_positions"
              else scrape_sh_skill_talent)
        all_records.extend(
            attempt(f"SH-{kind} {url}", lambda u=url, f=fn: f(u)))

    # dedupe on identity of the statistic
    seen, unique = set(), []
    for r in all_records:
        key = (r["indicator"], r["category"], r["region"], r["industry"],
               r["year"], r["source_url"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(unique, fh, ensure_ascii=False, indent=2)

    print("=" * 72)
    for name, status, n in report:
        print(f"[{status:>4}] {n:>4} records  {name}")
    print("=" * 72)
    print(f"total unique records: {len(unique)}")
    by_source = {}
    for r in unique:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    for src, n in sorted(by_source.items()):
        print(f"  {src}: {n}")
    print(f"output: {OUTPUT_FILE}")
    print("\nrobots status:")
    for host in ("https://www.stats.gov.cn", "https://rsj.sh.gov.cn"):
        print(f"  {host}: {check_robots(host)}")
    return 0 if unique else 1


if __name__ == "__main__":
    sys.exit(main())
