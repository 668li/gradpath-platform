# -*- coding: utf-8 -*-
"""国家统计局年度统计公报采集器（杠杆化 #4，2026-08-16）。

背景：统计年鉴近年（2015+）表格全部为 JPG 图片无法解析；统计局数据查询 API
（data.stats.gov.cn）403。唯一可低成本解析的宏观权威文本 = 年度统计公报
（每年 2 月底发布，含就业/失业/收入宏观指标）。

来源：https://www.stats.gov.cn/sj/zxfb/，URL 模式 t{YYYY}0228_{id}.html 稳定
（已实测确认 2022-2025 四年）。2026-02-28 发布《2025年公报》。

合规：stats.gov.cn 无 robots.txt（404）=> 不受限；单站 2 秒间隔；只取文本不碰图片。
安全：URL 全部为模块级常量 + 域名/路径白名单校验（validate_gongbao_url），
      与 base_crawler._validate_outbound_url 同语义；输出文件名固定字面量。
提取规则见 extract_gongbao_metrics()，带注释标记容忍（原文如"城镇新增就业[7]1267万人"）。

输出：stats_gongbao_data.json（同目录），字段与 salary_gov_data.json 一致。

Run:  py -3.13 stats_gongbao_scraper.py
"""
import json
import posixpath
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

# 输出文件与本脚本同目录，文件名固定字面量（禁止任何外部路径成分）
OUTPUT_FILE = Path(__file__).with_name("stats_gongbao_data.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
REQUEST_TIMEOUT = 30
POLITE_DELAY = 2.0

# 白名单：仅此主机 + 公报目录；其它任何 URL 直接拒绝（防 SSRF/误改）
ALLOWED_HOST = "www.stats.gov.cn"
ALLOWED_PATH_PREFIX = "/sj/zxfb/"

# (data_year, url) —— data_year 是公报所报告的年度（2026-02-28 发布 2025 年数据）
GONGBAO_PAGES = [
    (2025, "https://www.stats.gov.cn/sj/zxfb/202602/t20260228_1962662.html"),
    (2024, "https://www.stats.gov.cn/sj/zxfb/202502/t20250228_1958817.html"),
    (2023, "https://www.stats.gov.cn/sj/zxfb/202402/t20240228_1947915.html"),
    (2022, "https://www.stats.gov.cn/sj/zxfb/202302/t20230228_1919011.html"),
]
SOURCE = "国家统计局"


def validate_gongbao_url(url):
    """白名单校验（防御纵深）：仅 https + www.stats.gov.cn + /sj/zxfb/ 路径。

    路径先规范化再判定，拒绝任何 /../ 段（防路径穿越语义）。
    """
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != ALLOWED_HOST:
        raise ValueError(f"URL 不在白名单（host/协议）: {url}")
    norm_path = posixpath.normpath(parts.path)
    if not norm_path.startswith(ALLOWED_PATH_PREFIX):
        raise ValueError(f"URL 不在白名单（路径）: {url}")
    return url


def fetch(url):
    validate_gongbao_url(url)
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "ascii"):
        resp.encoding = "utf-8"
    return resp.text


def strip_to_text(html):
    """HTML → 纯文本：去 script/style/标签，压缩空白（保留数字与汉字连排）。"""
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text)


# 指标抽取正则（容忍公报注释标记 [7] 夹在数字前）
_PATTERNS = [
    # (indicator, category, unit, regex, group)
    ("全国就业人员数", "全体", "万人",
     r"年末全国就业人员\s*(?:\[\d+\])?\s*(\d+)\s*万人", 1),
    ("城镇就业人员数", "全体", "万人",
     r"其中城镇就业人员\s*(\d+)\s*万人", 1),
    ("城镇新增就业人数", "全体", "万人",
     r"全年(?:全国)?城镇新增就业\s*(?:\[\d+\])?\s*(\d+)\s*万人", 1),
    ("城镇调查失业率", "全体", "%",
     r"全年全国城镇调查失业率平均值为\s*(\d+\.\d+)\s*%", 1),
    ("农民工总量", "全体", "万人",
     r"全国农民工\s*(?:\[\d+\])?\s*总量\s*(\d+)\s*万人", 1),
    ("全国居民人均可支配收入", "全体", "元/年",
     r"全国居民人均可支配收入\s*(?:\[\d+\])?\s*(\d+)\s*元", 1),
    ("全国居民人均可支配收入", "城镇", "元/年",
     r"城镇居民人均可支配收入\s*(?:\[\d+\])?\s*(\d+)\s*元", 1),
    ("全国居民人均可支配收入", "农村", "元/年",
     r"农村居民人均可支配收入\s*(?:\[\d+\])?\s*(\d+)\s*元", 1),
]


def extract_gongbao_metrics(text, data_year, source_url, published_at):
    """从公报纯文本抽取指标记录列表（可测试：输入真实公报片段）。"""
    records = []
    for indicator, category, unit, pattern, group in _PATTERNS:
        m = re.search(pattern, text)
        if not m:
            continue
        value = float(m.group(group))
        records.append({
            "indicator": indicator,
            "category": category,
            "value": value,
            "unit": unit,
            "region": None,
            "industry": None,
            "year": data_year,
            "source": SOURCE,
            "source_url": source_url,
            "published_at": published_at,
        })
    return records


def scrape_gongbao(data_year, url):
    html = fetch(url)
    m = re.search(r"/t(\d{4})(\d{2})(\d{2})_", url)
    published_at = (f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                    if m else f"{data_year}-02-28")
    records = extract_gongbao_metrics(strip_to_text(html), data_year, url, published_at)
    return records


def main():
    all_records = []
    report = []
    for year, url in GONGBAO_PAGES:
        time.sleep(POLITE_DELAY)
        try:
            recs = scrape_gongbao(year, url)
            report.append((f"{year}公报 {url}", "OK", len(recs)))
            all_records.extend(recs)
        except Exception as exc:  # noqa: BLE001
            report.append((f"{year}公报 {url}", f"FAILED: {exc}", 0))

    # 幂等去重：同 indicator+category+year 只留一条
    seen, unique = set(), []
    for r in all_records:
        key = (r["indicator"], r["category"], r["year"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    OUTPUT_FILE.write_text(
        json.dumps(unique, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 72)
    for name, status, n in report:
        print(f"[{status:>4}] {n:>2} records  {name}")
    print("=" * 72)
    print(f"total unique records: {len(unique)}")
    print(f"output: {OUTPUT_FILE}")
    return 0 if unique else 1


if __name__ == "__main__":
    sys.exit(main())
