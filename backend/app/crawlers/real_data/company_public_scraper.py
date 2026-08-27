"""真实公司公开信息采集器（替换已删除的 53 条合成公司数据）。

合规红线（务必遵守）：
- 只用公开合规源（榜单公开页 / 交易所公开披露 / 行业协会官方公告附件）；
- 采集前检查 robots.txt，被禁止则跳过该源；
- 403 / 反爬拦截 → 如实记录并放弃该源，绝不绕过（不伪造来源、不重试轰炸）；
- 只取公开企业信息（名称 / 行业 / 规模 / 城市 / 官网 / 简介 / 榜单排名），
  不采集营收、利润等财务敏感明细（源数据中的财务字段一律丢弃）；
- 控频：每次请求间隔 1~2 秒随机。

数据源（3 个，均已验证）：
1. fortune_china500 —— 2025《财富》中国500强完整榜单
   https://www.caifuzhongwen.com/fortune500/rankings/china500/2025/
   （财富中文网 FORTUNE China 数据域名，robots.txt 全允许；
   页面内嵌 JSON 含 rank/name/industry/city/员工数，500 家）
2. isc_internet100 —— 中国互联网协会《中国互联网企业综合实力指数（2025）》
   官方公告附件 PDF（附件1：2025 年中国互联网综合实力前百家企业，100 家）
   https://www.isc.org.cn/article/27460980540829696.html
3. szse_listed —— 深圳证券交易所官网「上市公司列表」公开接口（A股，采样前 N 页）
   https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1110
   （交易所公开披露；需携带官网 Referer，属正常请求头）

输出：company_public_data.json（与本脚本同目录），纯数组，字段固定 8 个：
  {name, industry, size, city, description, website, source_url, rank}

运行：py -3.13 company_public_scraper.py [--sources fortune,isc,szse] [--szse-pages 3]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0"
REQUEST_DELAY = (1.0, 2.0)  # 每次请求间隔（秒，随机区间）
TIMEOUT = 40

FORTUNE_URL = "https://www.caifuzhongwen.com/fortune500/rankings/china500/2025/"
ISC_ARTICLE_URL = "https://www.isc.org.cn/article/27460980540829696.html"
ISC_PDF_URL = (
    "https://www.isc.org.cn/profile/2025/12/29/" "f531871d-ded7-4502-bb26-6d829f12707a.pdf"
)
SZSE_API = (
    "https://www.szse.cn/api/report/ShowReport/data"
    "?SHOWTYPE=JSON&CATALOGID=1110&TABKEY=tab1&PAGENO={page}"
)

OUT_PATH = Path(__file__).resolve().parent / "company_public_data.json"


@dataclass
class SourceReport:
    """单个数据源的运行结果（供最终如实报告）。"""

    name: str
    url: str
    status: str = "pending"  # ok / robots_disallowed / http_403 / blocked / error
    detail: str = ""
    count: int = 0
    robots_note: str = ""


@dataclass
class Scraper:
    sources: list = field(default_factory=list)
    session: requests.Session = field(default_factory=requests.Session)
    _robots_cache: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.session.headers.update({"User-Agent": USER_AGENT})

    # ------------------------------------------------------------------ #
    # 基础设施：控频 + robots.txt + 抓取
    # ------------------------------------------------------------------ #
    def _polite_sleep(self) -> None:
        time.sleep(random.uniform(*REQUEST_DELAY))

    def robots_allowed(self, url: str) -> tuple[bool, str]:
        """检查目标 URL 是否被 robots.txt 允许。

        robots.txt 返回 404 / 空 → 视为无限制（允许）；
        robots.txt 本身 403 / 5xx → 保守视为禁止抓取，如实记录。
        """
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base in self._robots_cache:
            return self._robots_cache[base]

        robots_url = f"{base}/robots.txt"
        note = f"{robots_url} "
        try:
            resp = self.session.get(robots_url, timeout=TIMEOUT)
            if resp.status_code == 200 and resp.text.strip():
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(resp.text.splitlines())
                allowed = rp.can_fetch(USER_AGENT, url)
                note += f"HTTP 200，{'允许' if allowed else '禁止'}抓取目标路径"
            elif resp.status_code == 200:
                allowed, note = True, note + "HTTP 200 但内容为空，视为无限制"
            elif resp.status_code == 404:
                allowed, note = True, note + "HTTP 404（无 robots.txt，视为无限制）"
            else:
                allowed = False
                note += f"HTTP {resp.status_code}，保守视为禁止"
        except requests.RequestException as exc:
            allowed, note = False, note + f"无法访问（{exc.__class__.__name__}），保守视为禁止"

        self._robots_cache[base] = (allowed, note)
        return allowed, note

    def fetch(self, url: str, referer: str | None = None) -> requests.Response:
        """抓取（调用方自行控频）。403 / 418 等直接抛 HTTPBlockedError 供上层放弃。"""
        headers = {"User-Agent": USER_AGENT}
        if referer:
            headers["Referer"] = referer
        resp = self.session.get(url, headers=headers, timeout=TIMEOUT)
        if resp.status_code in (403, 418, 429):
            raise HTTPBlockedError(f"HTTP {resp.status_code}（疑似反爬拦截），放弃该源")
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------ #
    # 源 1：2025《财富》中国500强
    # ------------------------------------------------------------------ #
    def scrape_fortune_china500(self) -> list[dict]:
        rep = SourceReport("fortune_china500", FORTUNE_URL)
        self.sources.append(rep)
        allowed, robots_note = self.robots_allowed(FORTUNE_URL)
        rep.robots_note = robots_note
        if not allowed:
            rep.status = "robots_disallowed"
            return []

        self._polite_sleep()
        try:
            # 显式按 UTF-8 解码，避免 requests 编码推断错误导致中文乱码
            html = self.fetch(FORTUNE_URL).content.decode("utf-8", errors="replace")
        except HTTPBlockedError as exc:
            rep.status, rep.detail = "blocked", str(exc)
            return []
        except requests.RequestException as exc:
            rep.status, rep.detail = "error", f"{exc.__class__.__name__}: {exc}"
            return []

        # 榜单数据以内嵌（JS 转义）JSON 形式存在于页面：{"data":[{"rk":1,"nm":...}]}
        marker = '{\\"data\\":'
        i = html.find(marker)
        if i < 0:
            rep.status, rep.detail = "error", "页面结构变化：未找到内嵌榜单 JSON"
            return []
        window = html[i:].replace('\\"', '"').replace("\\\\", "\\")
        try:
            obj, _ = json.JSONDecoder().raw_decode(window)
            records = obj["data"]
        except (json.JSONDecodeError, KeyError) as exc:
            rep.status, rep.detail = "error", f"内嵌 JSON 解析失败: {exc}"
            return []

        companies = []
        for r in records:
            name = (r.get("nm") or "").strip()
            if not name:
                continue
            rank = r.get("rk")
            industry = (r.get("ind") or "").strip()
            city = (r.get("city") or r.get("prov") or "").strip()
            emp = r.get("emp")  # 员工人数（公开规模信息）
            desc_parts = ["2025年《财富》中国500强企业"]
            if rank:
                desc_parts[0] = f"2025年《财富》中国500强第{rank}名"
            if industry:
                desc_parts.append(f"{industry}行业")
            if city:
                desc_parts.append(f"总部{city}")
            if emp:
                desc_parts.append(f"员工约{emp:,}人")
            companies.append(
                {
                    "name": name,
                    "industry": industry,
                    "size": _size_bucket(emp),
                    "city": city,
                    "description": "，".join(desc_parts) + "。",
                    "website": "",  # 源未披露官网，如实留空
                    "source_url": FORTUNE_URL,
                    "rank": rank,
                }
            )
        rep.status, rep.count = "ok", len(companies)
        # 注：源 JSON 中的营收/利润/ROE 等财务字段已按合规要求丢弃
        return companies

    # ------------------------------------------------------------------ #
    # 源 2：中国互联网协会 2025 互联网综合实力前百家企业（官方公告 PDF 附件）
    # ------------------------------------------------------------------ #
    def scrape_isc_internet100(self) -> list[dict]:
        rep = SourceReport("isc_internet100", ISC_ARTICLE_URL)
        self.sources.append(rep)
        try:
            import fitz  # PyMuPDF
        except ImportError:
            rep.status, rep.detail = "error", "未安装 PyMuPDF（py -3.13 -m pip install pymupdf）"
            return []

        allowed, robots_note = self.robots_allowed(ISC_PDF_URL)
        rep.robots_note = robots_note
        if not allowed:
            rep.status = "robots_disallowed"
            return []

        self._polite_sleep()
        try:
            pdf_bytes = self.fetch(ISC_PDF_URL).content
        except HTTPBlockedError as exc:
            rep.status, rep.detail = "blocked", str(exc)
            return []
        except requests.RequestException as exc:
            rep.status, rep.detail = "error", f"{exc.__class__.__name__}: {exc}"
            return []

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:  # noqa: BLE001
            rep.status, rep.detail = "error", f"PDF 打开失败: {exc}"
            return []

        # 「前5家（按企业名称笔划排序）」的竖排标记会拆成碎片并与前五行数据
        # 混在同一行/单独成行，需先剔除；附件2/附件3（成长型/网络安全榜）序号
        # 会重新从 1 开始，用「序号必须递增 + 满 100 家即停」防止混入其他名单。
        markers = {"前5家", "（按企", "业名称", "笔划排", "序）"}

        def is_company_name(text: str) -> bool:
            return len(text) >= 4 and ("公司" in text or "集团" in text)

        companies: list[dict] = []
        max_rank = 0
        for page in doc:
            text = page.get_text()
            if not companies and "前百家企业" not in text:
                continue  # 尚未进入附件1 名单页
            for table in page.find_tables().tables:
                for raw_row in table.extract():
                    cells = [re.sub(r"\s+", "", str(c)) for c in raw_row if c and str(c).strip()]
                    cells = [c for c in cells if c not in markers]
                    if not cells:
                        continue
                    joined = "".join(cells)
                    if "序号" in joined and "企业名称" in joined:
                        continue  # 表头
                    if len(companies) >= 100:
                        break  # 附件1 前100家已收满
                    if len(cells) >= 3 and re.fullmatch(r"[\u4e00-\u9fa5]{2,3}[省市]", cells[-1]):
                        # 数据行：[序号(可缺), 企业名称, 主要业务和品牌, 所属地]
                        location = cells[-1]
                        is_ranked = re.fullmatch(r"\d{1,3}", cells[0]) is not None
                        rank = int(cells[0]) if is_ranked else None
                        if is_ranked and rank <= max_rank:
                            break  # 序号重启 → 已进入附件2/附件3，停止
                        max_rank = max(max_rank, rank or 0)
                        name = cells[1] if is_ranked else cells[0]
                        business = cells[2] if is_ranked else cells[1]
                        if not is_company_name(name):
                            # 名称错位/异常行：尝试从其余单元格找回公司名
                            fix = next((c for c in cells[:-1] if is_company_name(c)), None)
                            if not fix:
                                continue  # 仍无法识别，宁缺毋滥
                            business = name if business == fix else business
                            name = fix
                        companies.append(
                            {
                                "name": name,
                                "industry": "互联网",
                                "size": "",  # 源未披露员工规模
                                "city": re.sub(r"市$", "", location),
                                "description": (
                                    "2025年中国互联网综合实力前百家企业（中国互联网协会），"
                                    f"主要业务与品牌：{business}。"
                                ),
                                "website": "",  # 源未披露官网
                                "source_url": ISC_ARTICLE_URL,
                                "rank": rank,  # 前5家按笔划排序，rank 为 null（如实）
                            }
                        )
                    elif companies and len(cells) == 1:
                        # 跨行续写：若上一条公司名疑似被截断（不以公司/集团结尾
                        # 且续写内容很短），并入公司名；否则并入业务简介
                        prev = companies[-1]
                        frag = cells[0]
                        if len(frag) <= 3 and not (
                            prev["name"].endswith("公司") or prev["name"].endswith("集团")
                        ):
                            prev["name"] += frag
                        else:
                            prev["description"] = prev["description"].rstrip("。") + frag + "。"
        # 采集结果自检：应恰为 100 家，前5名无序号、其余序号 6~100 不重不漏
        ranks = sorted(r["rank"] for r in companies if r["rank"] is not None)
        if (
            len(companies) != 100
            or ranks != list(range(6, 101))
            or any(not is_company_name(r["name"]) for r in companies)
        ):
            rep.status = "error"
            rep.detail = (
                f"附件1 解析自检未通过（{len(companies)} 家，"
                f"序号范围 {ranks[:1]}~{ranks[-1:] if ranks else []}），请人工复核"
            )
            return companies
        rep.status, rep.count = "ok", len(companies)
        rep.detail = f"名单来自官方公告附件 PDF：{ISC_PDF_URL}"
        return companies

    # ------------------------------------------------------------------ #
    # 源 3：深交所官网上市公司列表（公开接口，采样前 N 页）
    # ------------------------------------------------------------------ #
    def scrape_szse_listed(self, pages: int = 3) -> list[dict]:
        first_url = SZSE_API.format(page=1)
        rep = SourceReport("szse_listed", first_url)
        self.sources.append(rep)
        allowed, robots_note = self.robots_allowed("https://www.szse.cn/")
        rep.robots_note = robots_note
        if not allowed:
            rep.status = "robots_disallowed"
            return []

        companies: list[dict] = []
        for page in range(1, pages + 1):
            url = SZSE_API.format(page=page)
            self._polite_sleep()
            try:
                # 官网接口要求同站 Referer，属正常请求头（非绕过反爬）
                payload = self.fetch(url, referer="https://www.szse.cn/").json()
            except HTTPBlockedError as exc:
                rep.status, rep.detail = "blocked", str(exc)
                return companies  # 已采集的分页保留并如实报告
            except (requests.RequestException, json.JSONDecodeError) as exc:
                rep.status = "error"
                rep.detail = f"第{page}页失败 {exc.__class__.__name__}: {exc}"
                return companies
            rows = payload[0].get("data", []) if payload else []
            for row in rows:
                name = re.sub(r"<[^>]+>|\s+", "", str(row.get("agjc") or ""))
                code = (row.get("agdm") or "").strip()
                industry = re.sub(r"^[A-Z]\s*", "", str(row.get("sshymc") or "")).strip()
                board = (row.get("bk") or "").strip()
                if not name:
                    continue
                desc = f"深圳证券交易所{board}上市公司"
                if code:
                    desc += f"（股票代码 {code}）"
                if industry:
                    desc += f"，证监会行业分类：{industry}"
                companies.append(
                    {
                        "name": name,
                        "industry": industry,
                        "size": "",  # 接口未披露员工规模
                        "city": "",  # 接口未披露注册地（如实留空）
                        "description": desc + "。",
                        "website": "",
                        "source_url": url,
                        "rank": None,  # 列表按代码排序，无榜单排名
                    }
                )
            if not rows:
                break
        rep.status, rep.count = "ok", len(companies)
        rep.detail = f"采样前 {pages} 页（每页 20 家）"
        return companies


class HTTPBlockedError(RuntimeError):
    """目标站点返回 403/418/429，视为反爬拦截。"""


def _size_bucket(emp) -> str:
    """按公开员工人数给出规模区间标签；缺失返回空串。"""
    if not emp:
        return ""
    if emp >= 100000:
        return "100000人以上"
    if emp >= 10000:
        return "10000-99999人"
    if emp >= 5000:
        return "5000-9999人"
    if emp >= 1000:
        return "1000-4999人"
    if emp >= 500:
        return "500-999人"
    return "500人以下"


def main() -> int:
    parser = argparse.ArgumentParser(description="真实公司公开信息采集（合规版）")
    parser.add_argument(
        "--sources",
        default="fortune,isc,szse",
        help="逗号分隔：fortune / isc / szse（默认全部）",
    )
    parser.add_argument("--szse-pages", type=int, default=3, help="深交所采样页数（默认 3）")
    parser.add_argument("--out", default=str(OUT_PATH), help="输出 JSON 路径")
    args = parser.parse_args()

    scraper = Scraper()
    wanted = {s.strip() for s in args.sources.split(",") if s.strip()}
    all_companies: list[dict] = []

    if "fortune" in wanted:
        all_companies.extend(scraper.scrape_fortune_china500())
    if "isc" in wanted:
        all_companies.extend(scraper.scrape_isc_internet100())
    if "szse" in wanted:
        all_companies.extend(scraper.scrape_szse_listed(pages=args.szse_pages))

    # 按公司名去重（榜单间可能有交集，保留先出现的记录）
    seen: set[str] = set()
    deduped: list[dict] = []
    for c in all_companies:
        key = re.sub(r"\s+", "", c["name"])
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)

    out_path = Path(args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    # ---------------------------- 运行报告 ---------------------------- #
    print("=" * 72)
    print("采集报告（compliance-first，失败源如实列出）")
    print("=" * 72)
    for rep in scraper.sources:
        print(f"[{rep.status:>18}] {rep.name}  采集 {rep.count} 家")
        print(f"    URL: {rep.url}")
        if rep.robots_note:
            print(f"    robots: {rep.robots_note}")
        if rep.detail:
            print(f"    备注: {rep.detail}")
    print(f"合计（去重后）: {len(deduped)} 家 → {out_path}")
    print("=" * 72)
    return 0 if deduped else 1


if __name__ == "__main__":
    sys.exit(main())
