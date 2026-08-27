"""真实研究生导师公开简介 —— 大规模扩量采集器（在 mentor_edu_scraper.py 试点基础上扩量）。

合规红线（与 mentor_edu_scraper.py 完全一致，务必遵守）：
- 只用各大学官网（.edu.cn）公开的导师介绍 / 院系师资页；
- 采集前检查 robots.txt，被禁止则跳过该源；robots 404 → 视为无限制（允许）；
- robots 本身 403/5xx / 无法访问 → 保守视为禁止，如实记录；
- 403 / 418 / 429 → HTTPBlockedError，如实记录并放弃该源，绝不绕过、不重试轰炸；
- 只取公开简介字段：姓名 / 院校 / 院系 / 研究方向 / 职称 / 个人主页 URL。
  源页面中出现的电话、邮箱等联系方式一律丢弃，绝不入库；
  所有入库文本字段再经 sanitize() 防御性剥离邮箱/电话模式，结束后正则复查 0 泄漏；
- 控频：每次请求间隔 1~2 秒随机。

数据源（均已人工验证可访问，2026-08 探测）：
1. hust_all —— 华中科技大学「教师主页」系统大规模扩量（http://faculty.hust.edu.cn）
   列表：官方公开 JSON 接口 asyqueryteacher.jsp（页面脚本的数据源，参数一致），
   按 26 个拼音字母全量拉取（每字母一次请求，pagesize=800），仅保留
   gtutor（研究生导师）/ doctorTutor（博士生导师）字段为真的教师；
   详情：教师个人主页静态 HTML（所在单位 / 学科 / 研究方向区块）。
   断点续采：进度写入 --staging JSONL，重跑自动跳过已抓主页。
   注意：探测时 cs/iee/phy/life/civil 等 szu 子站与 sph.zju.edu.cn 均连接失败，
   仅下列四个源可用，如实记录于运行报告。
2. zju_bms_depts —— 浙江大学医学院基础医学系「师资队伍」按学科系分页
   https://bms.zju.edu.cn/8523{1..9}/list.htm、/85240/、/85241/
   （解剖学与组织胚胎学系 ~ 生物物理学系共 11 个学科系名录页，卡片结构同博导页）
3. szu_ce —— 深圳大学土木与交通工程学院「教师风采」
   （ce.szu.edu.cn 官方公开 JSON 接口 queryteacher.jsp + facultyce.szu.edu.cn 教师主页）
   注：任务建议的计算机（cs.szu.edu.cn 502/连接失败）与电子通信
   （iee.szu.edu.cn 连接失败）学院当前不可访问，改用可访问的土木与交通工程学院。
4. tongji_faculty —— 同济大学「教师个人主页」平台（faculty.tongji.edu.cn，
   与 HUST 同为 tsites 平台）拼音教师列表 + 教师个人主页。

输出（--out，默认 mentor_edu_expand.json）：纯数组，字段固定 7 个：
  {name, university, department, title, research_fields, homepage_url, source_url}
写入前自动与同目录 mentor_edu_data.json（现有 45 条）按 (name, university) 去重。

运行：
  py -3.13 mentor_edu_expand.py --unis hust --hust-limit 1600 --max-runtime 3300 \
      --out mentor_edu_expand.json
  py -3.13 mentor_edu_expand.py --unis zju,szu,tongji --per-uni 60
  py -3.13 mentor_edu_expand.py --merge a.json,b.json --out final.json   # 仅合并去重
"""

from __future__ import annotations

import argparse
import json
import random
import re
import string
import sys
import time
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0"
REQUEST_DELAY = (1.0, 2.0)  # 每次请求间隔（秒，随机区间）
TIMEOUT = 40

HERE = Path(__file__).resolve().parent
EXISTING_PATH = HERE / "mentor_edu_data.json"  # 现有 45 条，用于去重
DEFAULT_OUT = HERE / "mentor_edu_expand.json"
DEFAULT_STAGING = HERE / "mentor_edu_expand.staging.jsonl"

# --------------------------- 源 1：华中科技大学 --------------------------- #
HUST_BASE = "http://faculty.hust.edu.cn/"  # 站点仅 HTTP 可访问（HTTPS 握手失败）
HUST_LIST_API = "http://faculty.hust.edu.cn/system/resource/tsites/asy/asyqueryteacher.jsp"
HUST_LIST_REFERER = (
    "http://faculty.hust.edu.cn/pyjs.jsp"
    "?urltype=tsites.PinYinTeacherList&wbtreeid=1001&py={py}&lang=zh_CN"
)
# 参数来自官方拼音列表页自身渲染配置（wbtreeid=1001 页面源码），非绕过手段
HUST_VIEW_PARAMS = {
    "collegeid": 0,
    "disciplineid": 0,
    "rankid": 0,
    "honorid": 0,
    "viewmode": 8,
    "viewid": 1036549,
    "siteOwner": 1845635658,
    "viewUniqueId": 1036549,
    "showlang": "zh_CN",
    "type": "pyteacher",
}
HUST_ALL_LETTERS = tuple(string.ascii_lowercase)
HUST_PAGE_SIZE = 800  # 单字母最大 650（l），800 一次取完；不足时自动翻页

# ------------------------ 源 2：浙江大学 基础医学系 ------------------------ #
ZJU_BMS_DEPT_PAGES = {
    "85231": "解剖学与组织胚胎学系",
    "85232": "细胞生物学系",
    "85233": "遗传学系",
    "85234": "生理学系",
    "85235": "生物化学系",
    "85236": "病理学与病理生理学系",
    "85237": "免疫学系",
    "85238": "微生物学系",
    "85239": "药理学系",
    "85240": "干细胞与再生医学系",
    "85241": "生物物理学系",
}
ZJU_BMS_URL_TMPL = "https://bms.zju.edu.cn/{fid}/list.htm"

# --------------------- 源 3：深圳大学 土木与交通工程学院 --------------------- #
SZU_CE_BASE = "https://ce.szu.edu.cn/"
SZU_CE_LIST_API = "https://ce.szu.edu.cn/system/resource/tsites/portal/queryteacher.jsp"
SZU_CE_LIST_PAGE = "https://ce.szu.edu.cn/jsfc1.jsp?urltype=tree.TreeTempUrl&wbtreeid=1405"
# tsites_load_data_options（jsfc1.jsp 页面源码）中的渲染配置
SZU_CE_VIEW = {
    "collegeid": 0,
    "isshowpage": 1,
    "postdutyid": 0,
    "postdutyname": "",
    "facultyid": 0,
    "disciplineid": 0,
    "rankcode": "",
    "jobtypecode": "",
    "enrollid": 0,
    "login": "",
    "honorid": 0,
    "pinyin": "",
    "rankid": 0,
    "isbd": 0,
    "issd": 0,
    "teacherName": "",
    "searchDirection": "",
    "viewmode": 10,
    "viewOwner": 2091218752,
    "viewid": 1181411,
    "treeId": 1405,
    "reuqestUrl": "",
    "siteOwner": 2091218752,
    "actiontype": "advancesearch",
    "showlang": "zh_CN",
}
SZU_CE_POSTDUTY = (("1004", "教授"), ("1014", "副教授"))  # 官方「教师职称」筛选
SZU_CE_PAGE_SIZE = 50
SZU_CE_DETAIL_BASE = "http://facultyce.szu.edu.cn/"  # 教师主页（列表接口返回绝对地址）

# --------------------------- 源 4：同济大学 --------------------------- #
TONGJI_BASE = "https://faculty.tongji.edu.cn/"
TONGJI_LIST_TMPL = (
    "https://faculty.tongji.edu.cn/pinyin_teacherlist.jsp"
    "?urltype=tsites.PinYinTeacherList&wbtreeid=1001&py={py}&lang=zh_CN"
)
TONGJI_LETTERS = ("z", "l", "w", "c")  # 字母量大的优先，够用即止

# --------------------------- 隐私防护（合规） --------------------------- #
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
PHONE_RE = re.compile(r"(?<!\d)(?:1[3-9]\d{9}|\d{3,4}-\d{7,8}|400-?\d{3,4}-?\d{3,4})(?!\d)")


@dataclass
class SourceReport:
    """单个数据源的运行结果（供最终如实报告）。"""

    name: str
    url: str
    status: str = "pending"  # ok / robots_disallowed / http_403 / blocked / error
    detail: str = ""
    count: int = 0
    robots_note: str = ""


class HTTPBlockedError(RuntimeError):
    """目标站点返回 403/418/429，视为反爬拦截。"""


@dataclass
class Scraper:
    reports: list = field(default_factory=list)
    session: requests.Session = field(default_factory=requests.Session)
    _robots_cache: dict = field(default_factory=dict)
    deadline: float = 0.0  # >0 时为本次运行的软超时（time.time() 截止），超时优雅收尾

    def __post_init__(self) -> None:
        self.session.headers.update({"User-Agent": USER_AGENT})

    # ------------------------------------------------------------------ #
    # 基础设施：控频 + robots.txt + 抓取 + 隐私防护
    # ------------------------------------------------------------------ #
    def _polite_sleep(self) -> None:
        time.sleep(random.uniform(*REQUEST_DELAY))

    def time_left(self) -> bool:
        return self.deadline <= 0 or time.time() < self.deadline

    def robots_allowed(self, url: str) -> tuple[bool, str]:
        """检查目标 URL 是否被 robots.txt 允许。

        robots.txt 返回 404 / 空 → 视为无限制（允许）；
        robots.txt 本身 403 / 5xx / 无法访问 → 保守视为禁止抓取，如实记录。
        """
        from urllib.parse import urlparse

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

    def fetch(
        self,
        url: str,
        referer: str | None = None,
        params: dict | None = None,
    ) -> requests.Response:
        """抓取（调用方自行控频）。403 / 418 / 429 直接抛 HTTPBlockedError 供上层放弃。"""
        headers = {"User-Agent": USER_AGENT}
        if referer:
            headers["Referer"] = referer
        resp = self.session.get(url, headers=headers, params=params, timeout=TIMEOUT)
        if resp.status_code in (403, 418, 429):
            raise HTTPBlockedError(f"HTTP {resp.status_code}（疑似反爬拦截），放弃该源")
        resp.raise_for_status()
        return resp

    @staticmethod
    def _decode(resp: requests.Response) -> str:
        """按页面实际编码解码（.edu.cn 站点以 UTF-8 为主，失败回退 GBK 系）。"""
        text = resp.content.decode("utf-8", errors="replace")
        if "\ufffd" in text[:2000]:
            text = resp.content.decode("gb18030", errors="replace")
        return text

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").replace("\u00a0", " ")).strip(" ;；,，")

    @staticmethod
    def _strip_tags(html: str) -> str:
        plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
        plain = re.sub(r"<[^>]+>", " ", plain)
        return re.sub(r"\s+", " ", plain).replace("\u00a0", " ")

    @staticmethod
    def sanitize(text: str) -> str:
        """防御性剥离文本字段中可能混入的邮箱 / 电话模式（合规双保险）。"""
        text = EMAIL_RE.sub("", text or "")
        text = PHONE_RE.sub("", text)
        return re.sub(r"\s{2,}", " ", text).strip(" ;；,，")

    def sanitized(self, m: dict) -> dict:
        for k in ("name", "department", "title", "research_fields", "homepage_url", "source_url"):
            m[k] = self.sanitize(m.get(k, ""))
        return m

    # ------------------------------------------------------------------ #
    # tsites 教师主页详情解析（HUST / SZU-CE / Tongji 同平台复用）
    # ------------------------------------------------------------------ #
    def parse_tsites_detail(self, html: str) -> tuple[str, str]:
        """返回 (所在单位, 研究方向)。联系方式区块一律不解析。"""
        plain = self._strip_tags(html)
        m_dept = re.search(
            r"所在单位[：:]\s*(\S[^：:]{1,40}?)"
            r"(?:\s*学历|\s*学位|\s*学科|\s*性别|\s*其他联系方式|\s*个人简介|$)",
            plain,
        )
        m_res = re.search(
            r"研究方向</h2>.*?<div class=\"cont\">\s*(.*?)\s*</div>", html, flags=re.S
        )
        research = ""
        if m_res and "暂无" not in m_res.group(1):
            research = self._clean(self._strip_tags(m_res.group(1)))
        if not research:
            m_res2 = re.search(r"研究方向\s*[：:]\s*(\S[^。；;]{4,200}?)(?:。|；|$)", plain)
            if m_res2 and "暂无" not in m_res2.group(1):
                research = self._clean(m_res2.group(1))
        if not research:
            m_disc = re.search(
                r"学科[：:]\s*(\S[^：:]{1,80}?)"
                r"(?:\s*曾获荣誉|\s*教育经历|\s*工作经历|\s*团队成员|\s*论文成果|\s*招生信息|\s*其他联系方式|\s*个人简介|$)",
                plain,
            )
            research = self._clean(m_disc.group(1)) if m_disc else ""
        dept = self._clean(m_dept.group(1)) if m_dept else ""
        return dept, research

    # ------------------------------------------------------------------ #
    # 源 1：华中科技大学 教师主页系统（26 字母全量 + 断点续采）
    # ------------------------------------------------------------------ #
    def scrape_hust(
        self, limit: int, staging: Path, letters: tuple = HUST_ALL_LETTERS
    ) -> list[dict]:
        rep = SourceReport("hust_all", HUST_LIST_API)
        self.reports.append(rep)
        allowed, robots_note = self.robots_allowed(HUST_BASE)
        rep.robots_note = robots_note
        if not allowed:
            rep.status = "robots_disallowed"
            return []

        # 断点续采：已抓过的教师主页直接复用，不重复请求
        done: dict[str, dict] = {}
        if staging.exists():
            with open(staging, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("source") == "hust":
                        done[rec["mentor"]["homepage_url"]] = rec["mentor"]
        already = [m for m in done.values() if m["name"]]
        if len(already) >= limit:
            rep.status, rep.count = "ok", len(already)
            rep.detail = f"staging 已有 {len(already)} 条 ≥ 目标 {limit}，直接复用"
            return already[:limit]

        # 第一步：26 个拼音字母逐个全量拉取（gtutor/doctorTutor 过滤真导师）
        by_letter: dict[str, list[dict]] = {}
        list_err = ""
        for py in letters:
            if not self.time_left():
                rep.detail = "达到 --max-runtime 软超时，字母拉取中断"
                break
            rows: list[dict] = []
            pageindex = 1
            while True:
                self._polite_sleep()
                params = dict(HUST_VIEW_PARAMS, py=py, pageindex=pageindex, pagesize=HUST_PAGE_SIZE)
                try:
                    payload = self.fetch(
                        HUST_LIST_API,
                        referer=HUST_LIST_REFERER.format(py=py),
                        params=params,
                    ).json()
                except HTTPBlockedError as exc:
                    rep.status, rep.detail = "blocked", str(exc)
                    return list(done.values())
                except (requests.RequestException, json.JSONDecodeError) as exc:
                    list_err = f"{exc.__class__.__name__}: {exc}"
                    break
                batch = payload.get("teacherData", []) if isinstance(payload, dict) else []
                rows.extend(batch)
                total = int(payload.get("totalnum") or 0)
                if len(rows) >= total or not batch:
                    break
                pageindex += 1
            # 只保留明确标注研究生导师身份的教师；email 等字段一律不取
            by_letter[py] = [
                {
                    "name": self._clean(r.get("showName") or r.get("name") or ""),
                    "title": self._clean(r.get("prorank") or ""),
                    "doctor_tutor": bool(r.get("doctorTutor")),
                    "homepage_url": self._clean(r.get("url") or ""),
                }
                for r in rows
                if (r.get("gtutor") or r.get("doctorTutor"))
            ]
        # 字母间轮转（保证院系多样性）
        picked: list[dict] = []
        max_len = max((len(v) for v in by_letter.values()), default=0)
        for i in range(max_len):
            for py in letters:
                if i < len(by_letter.get(py, [])):
                    t = by_letter[py][i]
                    if t["name"] and t["homepage_url"] and t["homepage_url"] not in done:
                        picked.append(t)

        # 第二步：逐个抓教师主页，补全院系与研究方向；进度实时落盘
        mentors: list[dict] = list(done.values())
        fail = skip = 0
        for t in picked:
            if not self.time_left():
                rep.detail = (rep.detail + "；" if rep.detail else "") + (
                    f"达到 --max-runtime 软超时，详情抓取中断（已完成 {len(mentors)}）"
                )
                break
            if len(mentors) >= limit:
                break
            self._polite_sleep()
            try:
                html = self._decode(self.fetch(t["homepage_url"], referer=HUST_BASE))
            except HTTPBlockedError as exc:
                rep.status, rep.detail = "blocked", str(exc)
                break  # 已采部分保留并如实报告
            except requests.RequestException:
                fail += 1
                continue  # 单个主页失败跳过，不影响整源
            if "禁止开通主页" in html or "遇到错误" in html[:3000]:
                skip += 1
                continue  # 教师主页已停用（站点返回错误提示页），跳过
            dept, research = self.parse_tsites_detail(html)
            title = t["title"]
            if t["doctor_tutor"] and "博士生导师" not in title:
                title = f"{title}（博士生导师）" if title else "博士生导师"
            elif not title:
                title = "硕士生导师"  # 列表接口已确认其研究生导师身份
            m = {
                "name": t["name"],
                "university": "华中科技大学",
                "department": dept,
                "title": title,
                "research_fields": research,
                "homepage_url": t["homepage_url"],
                "source_url": t["homepage_url"],  # 教师主页即导师页原文
            }
            mentors.append(m)
            done[m["homepage_url"]] = m
            with open(staging, "a", encoding="utf-8") as f:
                f.write(json.dumps({"source": "hust", "mentor": m}, ensure_ascii=False) + "\n")
        rep.count = len(mentors)
        rep.status = "ok" if mentors else ("error" if not rep.detail else "partial")
        rep.detail = (
            (rep.detail + "；" if rep.detail else "")
            + f"26 字母列表全量 {sum(len(v) for v in by_letter.values())} 位导师候选，"
            f"详情成功 {len(mentors)}（主页失效跳过 {skip}，瞬时失败 {fail}），"
            f"断点续采 staging={staging.name}"
        )
        if list_err:
            rep.detail += f"；个别字母列表失败：{list_err}"
        return mentors

    # ------------------------------------------------------------------ #
    # 源 2：浙江大学 基础医学系 按学科系师资名录页（静态卡片，一页全量）
    # ------------------------------------------------------------------ #
    def scrape_zju(self, limit: int) -> list[dict]:
        rep = SourceReport("zju_bms_depts", "https://bms.zju.edu.cn/85241/list.htm")
        self.reports.append(rep)
        first_url = ZJU_BMS_URL_TMPL.format(fid=next(iter(ZJU_BMS_DEPT_PAGES)))
        allowed, robots_note = self.robots_allowed(first_url)
        rep.robots_note = robots_note
        if not allowed:
            rep.status = "robots_disallowed"
            return []

        mentors: list[dict] = []
        seen: set[str] = set()
        # 卡片结构与博导页一致：<div class="info"><a href="详情页">
        #   <h3>姓名</h3><span>职称</span></a><p>个人主页</p><p>所在学科系</p><p>研究方向</p></div>
        for fid, dept_name in ZJU_BMS_DEPT_PAGES.items():
            if len(mentors) >= limit or not self.time_left():
                break
            url = ZJU_BMS_URL_TMPL.format(fid=fid)
            self._polite_sleep()
            try:
                html = self._decode(self.fetch(url))
            except HTTPBlockedError as exc:
                rep.status, rep.detail = "blocked", str(exc)
                break
            except requests.RequestException as exc:
                rep.detail = (rep.detail + "；" if rep.detail else "") + (
                    f"{dept_name}页失败 {exc.__class__.__name__}"
                )
                continue
            got = 0
            for chunk in html.split('<div class="info">')[1:]:
                if len(mentors) >= limit:
                    break
                m_name = re.search(r"<h3>([^<]+)</h3>", chunk)
                if not m_name:
                    continue
                name = self._clean(m_name.group(1))
                key = "浙江大学|" + re.sub(r"\s+", "", name)
                if not name or not re.search(r"[\u4e00-\u9fa5A-Za-z]", name) or key in seen:
                    continue
                seen.add(key)
                m_title = re.search(r"</h3>\s*<span>([^<]*)</span>", chunk)
                m_res = re.search(r"研究方向</strong>[^<]*<span>([^<]*)</span>", chunk)
                m_home = re.search(
                    r"个人主页</strong>[^<]*<span>[^<]*</span></a>"
                    r'<a href="(https?://[^"]+)"[^>]*>',
                    chunk,
                )
                m_src = re.search(r'<a href="(/2024/\d+/\d+/[^"]+)"', chunk) or re.search(
                    r'<a href="([^"]+)"', chunk
                )
                mentors.append(
                    {
                        "name": name,
                        "university": "浙江大学",
                        "department": f"医学院基础医学系·{dept_name}",
                        "title": self._clean(m_title.group(1)) if m_title else "",
                        "research_fields": self._clean(m_res.group(1)) if m_res else "",
                        "homepage_url": self._clean(m_home.group(1)) if m_home else "",
                        "source_url": urljoin(url, m_src.group(1)) if m_src else url,
                    }
                )
                got += 1
        rep.count = len(mentors)
        rep.status = "ok" if mentors else "error"
        rep.detail = (
            f"基础医学系 11 个学科系师资名录页，采集 {len(mentors)} 位"
            f"（页面卡片中的其他字段未采集）"
        )
        return mentors

    # ------------------------------------------------------------------ #
    # 源 3：深圳大学 土木与交通工程学院 教师风采（JSON 列表 + 教师主页详情）
    # ------------------------------------------------------------------ #
    def scrape_szu_ce(self, limit: int) -> list[dict]:
        rep = SourceReport("szu_ce", SZU_CE_LIST_PAGE)
        self.reports.append(rep)
        allowed_ce, robots_ce = self.robots_allowed(SZU_CE_BASE)
        allowed_det, robots_det = self.robots_allowed(SZU_CE_DETAIL_BASE)
        rep.robots_note = robots_ce + " || " + robots_det
        if not (allowed_ce and allowed_det):
            rep.status = "robots_disallowed"
            return []

        # 第一步：官方「教师职称」筛选拉列表（教授优先，副教授补足）
        cards: list[dict] = []
        for duty_id, duty_name in SZU_CE_POSTDUTY:
            if len(cards) >= limit + 10:
                break
            pageindex = 1
            while True:
                if not self.time_left():
                    break
                self._polite_sleep()
                params = dict(
                    SZU_CE_VIEW,
                    postdutyid=duty_id,
                    pageindex=pageindex,
                    pagesize=SZU_CE_PAGE_SIZE,
                    profilelen=100,
                )
                try:
                    payload = self.fetch(
                        SZU_CE_LIST_API, referer=SZU_CE_LIST_PAGE, params=params
                    ).json()
                except HTTPBlockedError as exc:
                    rep.status, rep.detail = "blocked", str(exc)
                    return []
                except (requests.RequestException, json.JSONDecodeError) as exc:
                    rep.status, rep.detail = (
                        "error",
                        f"列表接口失败 {exc.__class__.__name__}: {exc}",
                    )
                    return []
                rows = payload.get("teacherData", []) if isinstance(payload, dict) else []
                for r in rows:  # email 等字段一律不取
                    url = self._clean(r.get("url") or "")
                    name = self._clean(r.get("showName") or r.get("name") or "")
                    if name and url:
                        cards.append({"name": name, "title": duty_name, "detail_url": url})
                total = int(payload.get("totalnum") or 0)
                if pageindex * SZU_CE_PAGE_SIZE >= total or not rows or len(cards) >= limit + 10:
                    break
                pageindex += 1

        # 第二步：教师主页详情（所在单位 / 研究方向；联系方式区块不解析）
        mentors: list[dict] = []
        fail = 0
        for c in cards:
            if len(mentors) >= limit or not self.time_left():
                break
            self._polite_sleep()
            try:
                html = self._decode(self.fetch(c["detail_url"], referer=SZU_CE_BASE))
            except HTTPBlockedError as exc:
                rep.status, rep.detail = "blocked", str(exc)
                break
            except requests.RequestException:
                fail += 1
                continue
            dept, research = self.parse_tsites_detail(html)
            if not research:
                # 「研究方向及兴趣」独立子页（教师主页导航 yjgk 栏目）
                m_sub = re.search(r'href="(/[^"]+/yjgk/\d+/list/index\.htm)"', html)
                if m_sub:
                    self._polite_sleep()
                    try:
                        sub = self._decode(
                            self.fetch(
                                urljoin(c["detail_url"], m_sub.group(1)), referer=c["detail_url"]
                            )
                        )
                        # 子页正文：<div class="content"><div class="subs"><p>研究方向…</p>
                        m_txt = re.search(
                            r'<div class="content">\s*<div class="subs">\s*<p>(.*?)</p>',
                            sub,
                            flags=re.S,
                        )
                        if m_txt and "暂无" not in m_txt.group(1):
                            research = self._clean(self._strip_tags(m_txt.group(1)))
                        if not research:
                            _, research = self.parse_tsites_detail(sub)
                    except (HTTPBlockedError, requests.RequestException):
                        research = ""
            mentors.append(
                {
                    "name": c["name"],
                    "university": "深圳大学",
                    "department": dept or "土木与交通工程学院",
                    "title": c["title"],
                    "research_fields": research,
                    "homepage_url": c["detail_url"],  # 学院教师主页即公开主页
                    "source_url": c["detail_url"],
                }
            )
        rep.count = len(mentors)
        rep.status = "ok" if mentors else "error"
        rep.detail = (
            f"教师职称筛选（{'/'.join(n for _, n in SZU_CE_POSTDUTY)}）列表 {len(cards)} 人，"
            f"详情成功 {len(mentors)}（失败 {fail}）；列表接口返回的邮箱等字段未采集"
        )
        return mentors

    # ------------------------------------------------------------------ #
    # 源 4：同济大学 教师个人主页（拼音列表 + 教师主页详情）
    # ------------------------------------------------------------------ #
    def scrape_tongji(self, limit: int) -> list[dict]:
        rep = SourceReport("tongji_faculty", TONGJI_BASE + "pinyin_teacherlist.jsp")
        self.reports.append(rep)
        allowed, robots_note = self.robots_allowed(TONGJI_BASE)
        rep.robots_note = robots_note
        if not allowed:
            rep.status = "robots_disallowed"
            return []

        # 第一步：拼音列表页（服务端渲染：<li><a href=主页><p>姓名</p><p>单位</p></a></li>）
        cards: list[dict] = []
        for py in TONGJI_LETTERS:
            if len(cards) >= limit + 10:
                break
            page = 1
            while True:
                if not self.time_left():
                    break
                url = TONGJI_LIST_TMPL.format(py=py)
                if page > 1:
                    url += f"&PAGENUM={page}"
                self._polite_sleep()
                try:
                    html = self._decode(self.fetch(url, referer=TONGJI_BASE))
                except HTTPBlockedError as exc:
                    rep.status, rep.detail = "blocked", str(exc)
                    return []
                except requests.RequestException as exc:
                    rep.status, rep.detail = "error", f"列表页失败 {exc.__class__.__name__}"
                    return []
                for m in re.finditer(
                    r'<a href="(https?://faculty\.tongji\.edu\.cn/[^"]+?)">\s*'
                    r'<div class="pic">.*?</div>\s*<p>([^<]+)</p>\s*<p>([^<]*)</p>',
                    html,
                    flags=re.S,
                ):
                    name, unit = self._clean(m.group(2)), self._clean(m.group(3))
                    if name and re.search(r"[\u4e00-\u9fa5A-Za-z]", name):
                        cards.append({"name": name, "unit": unit, "detail_url": m.group(1)})
                m_total = re.search(r"共(\d+)条.*?(\d+)/(\d+)", html)
                if not m_total or page >= int(m_total.group(3)) or len(cards) >= limit + 10:
                    break
                page += 1

        # 第二步：教师主页详情（学科 / 个人简介中的职称与研究方向；邮箱已混淆亦不解析）
        mentors: list[dict] = []
        fail = 0
        for c in cards:
            if len(mentors) >= limit or not self.time_left():
                break
            self._polite_sleep()
            try:
                html = self._decode(self.fetch(c["detail_url"], referer=TONGJI_BASE))
            except HTTPBlockedError as exc:
                rep.status, rep.detail = "blocked", str(exc)
                break
            except requests.RequestException:
                fail += 1
                continue
            plain = self._strip_tags(html)
            dept, research = self.parse_tsites_detail(html)
            if not research:
                m_rd = re.search(r"主要研究方向[为是：:]+\s*([^。；;]{4,150})", plain)
                if m_rd:
                    research = self._clean(m_rd.group(1))
            # 职称：个人简介文本中的「××教授/研究员，博士生导师」模式
            title = ""
            m_t = re.search(
                r"[\u4e00-\u9fa5]{0,8}?((?:长聘|特聘|客座|兼职)?(?:副)?(?:教授|研究员)"
                r"|(?:助理教授|讲师|高级工程师|实验师))(?:[，,、]\s*(?:博士生导师|硕士生导师))?",
                plain,
            )
            if m_t:
                title = self._clean(m_t.group(1))
                if "博士生导师" in plain[:6000]:
                    title += "（博士生导师）"
            mentors.append(
                {
                    "name": c["name"],
                    "university": "同济大学",
                    "department": dept or c["unit"] or "",
                    "title": title,
                    "research_fields": research,
                    "homepage_url": c["detail_url"],
                    "source_url": c["detail_url"],
                }
            )
        rep.count = len(mentors)
        rep.status = "ok" if mentors else "error"
        rep.detail = (
            f"拼音字母 {'/'.join(TONGJI_LETTERS)} 列表 {len(cards)} 人，详情成功 {len(mentors)}"
            f"（失败 {fail}）；详情页中的电子邮箱（混淆串）与联系方式未解析"
        )
        return mentors


# --------------------------------------------------------------------------- #
# 汇总：去重 + 隐私复查 + 写文件
# --------------------------------------------------------------------------- #
def dedup_key(m: dict) -> str:
    return m.get("university", "") + "|" + re.sub(r"\s+", "", m.get("name", ""))


def load_existing() -> list[dict]:
    if EXISTING_PATH.exists():
        with open(EXISTING_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def audit_leaks(mentors: list[dict]) -> tuple[int, list[str]]:
    """正则复查输出中是否残留邮箱 / 电话（必须为 0）。"""
    hits: list[str] = []
    for m in mentors:
        for k, v in m.items():
            if not isinstance(v, str):
                continue
            for pat in (EMAIL_RE, PHONE_RE):
                mm = pat.search(v)
                if mm:
                    hits.append(f"{m.get('name')}.{k}={mm.group(0)}")
    return len(hits), hits[:10]


def finalize(mentors: list[dict], out_path: Path, scraper_reports: list[SourceReport]) -> int:
    existing = load_existing()
    existing_keys = {dedup_key(m) for m in existing}
    seen: set[str] = set()
    deduped: list[dict] = []
    for m in mentors:
        key = dedup_key(m)
        if m.get("name") and key not in seen and key not in existing_keys:
            seen.add(key)
            deduped.append(m)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    # ---------------------------- 运行报告 ---------------------------- #
    print("=" * 72)
    print("导师扩量采集报告（compliance-first，失败源如实列出）")
    print(f"时间: {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 72)
    for rep in scraper_reports:
        print(f"[{rep.status:>18}] {rep.name}  采集 {rep.count} 位")
        print(f"    URL: {rep.url}")
        if rep.robots_note:
            print(f"    robots: {rep.robots_note}")
        if rep.detail:
            print(f"    备注: {rep.detail}")
    by_uni: dict[str, int] = {}
    for m in deduped:
        by_uni[m["university"]] = by_uni.get(m["university"], 0) + 1
    for uni, n in by_uni.items():
        print(f"  {uni}: {n} 位")
    n_leak, leak_samples = audit_leaks(deduped)
    n_dup_existing = len([1 for m in mentors if dedup_key(m) in existing_keys])
    print(
        f"现有库 {len(existing)} 条（mentor_edu_data.json），与现有库重复剔除 {n_dup_existing} 条，"
        f"批内重复剔除 {len(mentors) - n_dup_existing - len(deduped)} 条"
    )
    print(f"合计（与现有 45 条去重后的净新增）: {len(deduped)} 位 → {out_path}")
    print(
        f"联系方式泄漏复查（邮箱/电话正则）: {n_leak} 处"
        + (f"，样例: {leak_samples}" if n_leak else "，通过（0 泄漏）")
    )
    print("=" * 72)
    return 0 if deduped else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="真实研究生导师公开简介 · 大规模扩量采集")
    parser.add_argument(
        "--unis",
        default="hust,zju,szu,tongji",
        help="逗号分隔：hust / zju / szu / tongji（zju=基础医学系各学科系，szu=土木与交通工程学院）",
    )
    parser.add_argument(
        "--per-uni", type=int, default=60, help="小规模源每源条数（zju/szu/tongji，默认 60）"
    )
    parser.add_argument("--hust-limit", type=int, default=1600, help="HUST 目标条数（默认 1600）")
    parser.add_argument(
        "--max-runtime",
        type=int,
        default=0,
        help="软超时秒数（0=不限），到点后优雅收尾，可配合 staging 断点续采",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="输出 JSON 路径")
    parser.add_argument("--staging", default=str(DEFAULT_STAGING), help="HUST 断点续采 JSONL 路径")
    parser.add_argument(
        "--merge",
        default="",
        help="仅合并模式：逗号分隔的多个结果 JSON，合并去重后写入 --out（不联网）",
    )
    args = parser.parse_args()

    if args.merge:  # 离线合并多个分段运行的结果
        merged: list[dict] = []
        for p in args.merge.split(","):
            fp = Path(p.strip())
            if fp.exists():
                with open(fp, encoding="utf-8") as f:
                    merged.extend(json.load(f))
            else:
                print(f"[merge] 跳过不存在的结果文件: {fp}")
        return finalize(merged, Path(args.out), [])

    scraper = Scraper()
    if args.max_runtime > 0:
        scraper.deadline = time.time() + args.max_runtime
    wanted = {u.strip() for u in args.unis.split(",") if u.strip()}
    mentors: list[dict] = []
    # 先跑小源（快），再跑 HUST 大源（可断点续采）
    if "zju" in wanted:
        mentors.extend(scraper.scrape_zju(args.per_uni))
    if "szu" in wanted:
        mentors.extend(scraper.scrape_szu_ce(args.per_uni))
    if "tongji" in wanted:
        mentors.extend(scraper.scrape_tongji(args.per_uni))
    if "hust" in wanted:
        mentors.extend(scraper.scrape_hust(args.hust_limit, Path(args.staging)))
    mentors = [scraper.sanitized(m) for m in mentors]
    return finalize(mentors, Path(args.out), scraper.reports)


if __name__ == "__main__":
    sys.exit(main())
