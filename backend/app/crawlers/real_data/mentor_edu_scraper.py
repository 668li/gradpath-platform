# -*- coding: utf-8 -*-
"""真实研究生导师公开简介采集器（3 校试点：浙江大学 / 华中科技大学 / 深圳大学）。

合规红线（务必遵守，模式与 company_public_scraper.py 一致）：
- 只用各大学官网（.edu.cn）公开的导师介绍 / 院系师资页；
- 采集前检查 robots.txt，被禁止则跳过该源；robots 本身 403/5xx → 保守视为禁止；
- 403 / 418 / 429 → HTTPBlockedError，如实记录并放弃该源，绝不绕过、不重试轰炸；
- 只取公开简介字段：姓名 / 院校 / 院系 / 研究方向 / 职称 / 个人主页 URL。
  源页面中出现的电话、邮箱等联系方式一律丢弃，绝不入库；
- 控频：每次请求间隔 1~2 秒随机；
- 不访问 yz.chsi.com.cn。

数据源（3 个，均已人工验证可访问）：
1. zju_bms —— 浙江大学基础医学系「博士生导师名录」（静态卡片：姓名/职称/学科系/研究方向/个人主页）
   https://bms.zju.edu.cn/85230/list.htm
   （注：yjs.zju.edu.cn 研究生院站点当前 502 / TLS 握手失败，改用院系官网公开博导名录）
2. hust_faculty —— 华中科技大学「教师主页」系统（faculty.hust.edu.cn，HTTP）
   列表：官方页面自身调用的公开 JSON 接口（页面脚本 asyqueryteacher.js 的数据源，
   参数与官方页面一致），按姓氏拼音采样；
   详情：教师个人主页静态 HTML（所在单位 / 学科 / 研究方向区块）。
3. szu_math —— 深圳大学数学科学学院「师资一览」（按字母总表 + 教师详情页）
   https://math.szu.edu.cn/szdw/szyl/azm/All.htm
   （注：SZU 无全校统一公开导师库，采用院系师资页；详情页含「研究领域」区块）

输出：mentor_edu_data.json（与本脚本同目录），纯数组，字段固定 7 个：
  {name, university, department, title, research_fields, homepage_url, source_url}

运行：py -3.13 mentor_edu_scraper.py [--unis zju,hust,szu] [--per-uni 15]
"""
from __future__ import annotations

import argparse
import io
import json
import random
import re
import sys
import time
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin
from urllib.parse import urlparse

import requests

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0"
REQUEST_DELAY = (1.0, 2.0)  # 每次请求间隔（秒，随机区间）
TIMEOUT = 40

ZJU_LIST_URL = "https://bms.zju.edu.cn/85230/list.htm"  # 浙大基础医学系博导名录

HUST_BASE = "http://faculty.hust.edu.cn/"  # 站点仅 HTTP 可访问（HTTPS 握手失败）
HUST_LIST_API = (
    "http://faculty.hust.edu.cn/system/resource/tsites/asy/asyqueryteacher.jsp"
)
HUST_LIST_REFERER = (
    "http://faculty.hust.edu.cn/pyjs.jsp"
    "?urltype=tsites.PinYinTeacherList&wbtreeid=1001&py={py}&lang=zh_CN"
)
# 以下参数来自官方拼音列表页自身渲染配置（wbtreeid=1001 页面源码），非绕过手段
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
HUST_SAMPLE_LETTERS = ("z", "c", "w")  # 按姓氏拼音采样，增加院系多样性

SZU_LIST_URL = "https://math.szu.edu.cn/szdw/szyl/azm/All.htm"  # 深大数学学院师资一览

OUT_PATH = Path(__file__).resolve().parent / "mentor_edu_data.json"


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

    # ------------------------------------------------------------------ #
    # 源 1：浙江大学 基础医学系 博士生导师名录（静态卡片，一页全量）
    # ------------------------------------------------------------------ #
    def scrape_zju(self, limit: int) -> list[dict]:
        rep = SourceReport("zju_bms", ZJU_LIST_URL)
        self.reports.append(rep)
        allowed, robots_note = self.robots_allowed(ZJU_LIST_URL)
        rep.robots_note = robots_note
        if not allowed:
            rep.status = "robots_disallowed"
            return []

        self._polite_sleep()
        try:
            html = self._decode(self.fetch(ZJU_LIST_URL))
        except HTTPBlockedError as exc:
            rep.status, rep.detail = "blocked", str(exc)
            return []
        except requests.RequestException as exc:
            rep.status, rep.detail = "error", f"{exc.__class__.__name__}: {exc}"
            return []

        mentors: list[dict] = []
        # 卡片结构：<div class="info"><a href="详情页"><h3>姓名</h3><span>职称</span></a>
        #           <p>个人主页链接</p><p>所在学科系</p><p>研究方向</p></div>
        for chunk in html.split('<div class="info">')[1:]:
            m_name = re.search(r"<h3>([^<]+)</h3>", chunk)
            if not m_name:
                continue
            name = self._clean(m_name.group(1))
            if not re.search(r"[\u4e00-\u9fa5A-Za-z]", name):
                continue
            m_title = re.search(r"</h3>\s*<span>([^<]*)</span>", chunk)
            m_dept = re.search(r"所在学科系</strong>[^<]*<span>([^<]*)</span>", chunk)
            m_res = re.search(r"研究方向</strong>[^<]*<span>([^<]*)</span>", chunk)
            m_home = re.search(
                r'个人主页</strong>[^<]*<span>[^<]*</span></a>'
                r'<a href="(https?://[^"]+)"[^>]*>',
                chunk,
            )
            m_src = re.search(r'<a href="(/2024/\d+/\d+/[^"]+)"', chunk) or re.search(
                r'<a href="([^"]+)"', chunk
            )
            dept = self._clean(m_dept.group(1)) if m_dept else ""
            mentors.append(
                {
                    "name": name,
                    "university": "浙江大学",
                    "department": f"医学院基础医学系·{dept}" if dept else "医学院基础医学系",
                    "title": self._clean(m_title.group(1)) if m_title else "",
                    "research_fields": self._clean(m_res.group(1)) if m_res else "",
                    "homepage_url": self._clean(m_home.group(1)) if m_home else "",
                    "source_url": urljoin(ZJU_LIST_URL, m_src.group(1)) if m_src else ZJU_LIST_URL,
                }
            )
            if len(mentors) >= limit:
                break
        rep.status, rep.count = "ok", len(mentors)
        rep.detail = f"页面为「博士生导师名录」，采样前 {len(mentors)} 位（全页静态卡片）"
        return mentors

    # ------------------------------------------------------------------ #
    # 源 2：华中科技大学 教师主页系统（公开 JSON 列表 + 教师主页详情）
    # ------------------------------------------------------------------ #
    def scrape_hust(self, limit: int) -> list[dict]:
        rep = SourceReport("hust_faculty", HUST_LIST_API)
        self.reports.append(rep)
        allowed, robots_note = self.robots_allowed(HUST_BASE)
        rep.robots_note = robots_note
        if not allowed:
            rep.status = "robots_disallowed"
            return []

        # 第一步：按拼音字母取列表（官方页面自身调用的公开 JSON 接口）
        candidates: list[dict] = []
        for py in HUST_SAMPLE_LETTERS:
            self._polite_sleep()
            params = dict(HUST_VIEW_PARAMS, py=py, pageindex=1, pagesize=50)
            try:
                payload = self.fetch(
                    HUST_LIST_API, referer=HUST_LIST_REFERER.format(py=py), params=params
                ).json()
            except HTTPBlockedError as exc:
                rep.status, rep.detail = "blocked", str(exc)
                return []
            except (requests.RequestException, json.JSONDecodeError) as exc:
                rep.status, rep.detail = "error", f"列表接口失败 {exc.__class__.__name__}: {exc}"
                return []
            rows = payload.get("teacherData", []) if isinstance(payload, dict) else []
            # 只保留明确标注研究生导师身份的教师；email 等字段一律不取
            for row in rows:
                if row.get("gtutor") or row.get("doctorTutor"):
                    candidates.append(
                        {
                            "name": self._clean(row.get("showName") or row.get("name") or ""),
                            "title": self._clean(row.get("prorank") or ""),
                            "doctor_tutor": bool(row.get("doctorTutor")),
                            "homepage_url": self._clean(row.get("url") or ""),
                        }
                    )
            if len(candidates) >= limit * 3:
                break
        # 字母间轮转排序，保证院系多样性；不截断，详情抓取时遇到
        # 失效主页/瞬时失败可顺延到下一位，直到凑满目标条数
        picked: list[dict] = []
        for i in range(max(len(candidates) // len(HUST_SAMPLE_LETTERS), 1)):
            for py_idx in range(len(HUST_SAMPLE_LETTERS)):
                idx = i * len(HUST_SAMPLE_LETTERS) + py_idx
                if idx < len(candidates) and candidates[idx]["name"] and candidates[idx]["homepage_url"]:
                    picked.append(candidates[idx])

        # 第二步：逐个抓教师主页，补全院系（所在单位）与研究方向（学科/研究方向区块）
        mentors: list[dict] = []
        for t in picked:
            self._polite_sleep()
            try:
                html = self._decode(self.fetch(t["homepage_url"], referer=HUST_BASE))
            except HTTPBlockedError as exc:
                rep.status, rep.detail = "blocked", str(exc)
                break  # 已采部分保留并如实报告
            except requests.RequestException:
                continue  # 单个主页失败跳过，不影响整源
            if "禁止开通主页" in html or "遇到错误" in html[:3000]:
                continue  # 教师主页已停用（站点返回错误提示页），跳过
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
                m_disc = re.search(
                    r"学科[：:]\s*(\S[^：:]{1,80}?)"
                    r"(?:\s*曾获荣誉|\s*教育经历|\s*工作经历|\s*团队成员|\s*论文成果|\s*招生信息|\s*其他联系方式|\s*个人简介|$)",
                    plain,
                )
                research = self._clean(m_disc.group(1)) if m_disc else ""
            title = t["title"]
            if t["doctor_tutor"] and "博士生导师" not in title:
                title = f"{title}（博士生导师）" if title else "博士生导师"
            elif not title:
                title = "硕士生导师"  # 列表接口已确认其研究生导师身份
            mentors.append(
                {
                    "name": t["name"],
                    "university": "华中科技大学",
                    "department": self._clean(m_dept.group(1)) if m_dept else "",
                    "title": title,
                    "research_fields": research,
                    "homepage_url": t["homepage_url"],
                    "source_url": t["homepage_url"],  # 教师主页即导师页原文
                }
            )
            if len(mentors) >= limit:
                break
        rep.count = len(mentors)
        rep.status = "ok" if len(mentors) >= min(limit, 1) else "error"
        rep.detail = f"教师主页系统（tsites），字母采样 {HUST_SAMPLE_LETTERS}，详情 {len(mentors)} 位"
        return mentors

    # ------------------------------------------------------------------ #
    # 源 3：深圳大学 数学科学学院 师资一览（总表卡片 + 教师详情页）
    # ------------------------------------------------------------------ #
    def scrape_szu(self, limit: int) -> list[dict]:
        rep = SourceReport("szu_math", SZU_LIST_URL)
        self.reports.append(rep)
        allowed, robots_note = self.robots_allowed(SZU_LIST_URL)
        rep.robots_note = robots_note
        if not allowed:
            rep.status = "robots_disallowed"
            return []

        self._polite_sleep()
        try:
            html = self._decode(self.fetch(SZU_LIST_URL))
        except HTTPBlockedError as exc:
            rep.status, rep.detail = "blocked", str(exc)
            return []
        except requests.RequestException as exc:
            rep.status, rep.detail = "error", f"{exc.__class__.__name__}: {exc}"
            return []

        # 卡片结构：<li><a class="flex" href="../../../info/1072/xxxx.htm">...
        #   <h5>姓名</h5><p>职称：教授</p> ...
        # 注意：卡片中同时含电话/邮箱行，按合规要求一律不解析、不入库。
        cards: list[dict] = []
        for m in re.finditer(
            r'<a class="flex" href="(\.\./\.\./\.\./info/\d+/\d+\.htm)">.*?<h5>([^<]+)</h5>(.*?)</a>',
            html,
            flags=re.S,
        ):
            detail_url = urljoin(SZU_LIST_URL, m.group(1))
            name = self._clean(m.group(2))
            body = m.group(3)
            m_title = re.search(r"职称[：:]\s*([^<\s]+)", body)
            title = self._clean(m_title.group(1)) if m_title else ""
            # 优先教授/副教授/研究员（学院导师主体）；不足时放宽
            cards.append({"name": name, "title": title, "detail_url": detail_url})
        # 优先教授/副教授/研究员（学院研究生导师主体），不足再放宽；多取几个作失败缓冲
        preferred = [c for c in cards if re.search(r"教授|研究员", c["title"])]
        others = [c for c in cards if c not in preferred]
        picked = (preferred + others)[: limit + 5]

        mentors: list[dict] = []
        for c in picked:
            self._polite_sleep()
            try:
                dhtml = self._decode(self.fetch(c["detail_url"], referer=SZU_LIST_URL))
            except HTTPBlockedError as exc:
                rep.status, rep.detail = "blocked", str(exc)
                break
            except requests.RequestException:
                continue
            plain = self._strip_tags(dhtml)
            m_res = re.search(
                r"研究领域\s*(.*?)\s*(?:获得荣誉|教学课程|科研成果|主持项目|社会任职|主持科研项目|$)",
                plain,
            )
            research = self._clean(m_res.group(1)) if m_res else ""
            mentors.append(
                {
                    "name": c["name"],
                    "university": "深圳大学",
                    "department": "数学科学学院",
                    "title": c["title"],
                    "research_fields": research,
                    "homepage_url": c["detail_url"],  # 学院官网教师页即公开主页
                    "source_url": c["detail_url"],
                }
            )
            if len(mentors) >= limit:
                break
        rep.count = len(mentors)
        rep.status = "ok" if mentors else "error"
        rep.detail = (
            f"师资一览共 {len(cards)} 人（教授/研究员类 {len(preferred)} 人），"
            f"采样详情 {len(mentors)} 位；卡片中的电话/邮箱字段未采集"
        )
        return mentors


def main() -> int:
    parser = argparse.ArgumentParser(description="真实研究生导师公开简介采集（3 校试点）")
    parser.add_argument("--unis", default="zju,hust,szu", help="逗号分隔：zju / hust / szu")
    parser.add_argument("--per-uni", type=int, default=15, help="每校采样条数（默认 15）")
    parser.add_argument("--out", default=str(OUT_PATH), help="输出 JSON 路径")
    args = parser.parse_args()

    scraper = Scraper()
    wanted = {u.strip() for u in args.unis.split(",") if u.strip()}
    mentors: list[dict] = []
    if "zju" in wanted:
        mentors.extend(scraper.scrape_zju(args.per_uni))
    if "hust" in wanted:
        mentors.extend(scraper.scrape_hust(args.per_uni))
    if "szu" in wanted:
        mentors.extend(scraper.scrape_szu(args.per_uni))

    # 按 院校+姓名 去重（保留先出现的记录）
    seen: set[str] = set()
    deduped: list[dict] = []
    for m in mentors:
        key = f"{m['university']}|{re.sub(r'\s+', '', m['name'])}"
        if key not in seen and m["name"]:
            seen.add(key)
            deduped.append(m)

    out_path = Path(args.out)
    with io.open(out_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    # ---------------------------- 运行报告 ---------------------------- #
    print("=" * 72)
    print("导师采集报告（compliance-first，失败源如实列出）")
    print("=" * 72)
    for rep in scraper.reports:
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
    print(f"合计（去重后）: {len(deduped)} 位 → {out_path}")
    print("=" * 72)
    return 0 if deduped else 1


if __name__ == "__main__":
    sys.exit(main())
