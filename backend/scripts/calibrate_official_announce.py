"""official_announce 扩校标定脚本：真实抓取各校研究生院公开栏目并验证可解析性。

为 DEFAULT_SECTIONS 扩校做人工标定（2026-09 扩校任务）。合规边界：
- 只访问各校研究生院官网公开栏目（*.edu.cn），绝不触碰 yz.chsi.com.cn（红线）
- 复用 OfficialAnnounceCrawler._request：robots fail-safe + SSRF 护栏 + ≥1.5s 限速
- 验收线：列表页 parse_list_generic ≥5 条且最新日期 ≤18 个月内、URL 同域；
  详情页 extract_main_text 正文 ≥80 字
- 全部达标才收进 DEFAULT_SECTIONS；被 WAF/robots 挡下的如实记录

用法（backend/ 目录下）：
    py -3.13 scripts/calibrate_official_announce.py whu xjtu          # 标定指定校
    py -3.13 scripts/calibrate_official_announce.py --all             # 全部候选校
    py -3.13 scripts/calibrate_official_announce.py whu --save        # 达标后存夹具
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.crawlers.research.official_announce_crawler import (  # noqa: E402
    OfficialAnnounceCrawler,
    _parse_list_entries,
    extract_main_text,
    parse_list_generic,
)

FIXTURE_DIR = BACKEND / "tests" / "fixtures" / "official_announce"
CUTOFF = "2025-03-05"  # 18 个月前（2026-09-05 起）
MIN_ENTRIES = 5
MIN_DETAIL_LEN = 80

# 每校：研究生院官网首页候选（DNS 已本地预筛）+ 静态猜测栏目（都会先经首页自动发现补充候选）
# 注：yz.*.edu.cn 为该校研究生院/研招办运营的招生信息网（校级官方域名，非 chsi）；
# 仅当研究生院主站不可达/被 WAF 挡时作为候选，PROGRESS 中如实记录。
CANDIDATE_SCHOOLS: dict[str, dict] = {
    "whu": {"name": "武汉大学研究生院", "homes": ["https://gs.whu.edu.cn/", "https://yz.whu.edu.cn/"], "guess": []},
    "hust": {"name": "华中科技大学研究生院", "homes": ["https://gs.hust.edu.cn/"], "guess": []},
    "nju": {"name": "南京大学研究生院", "homes": ["https://yzb.nju.edu.cn/"], "guess": []},
    "seu": {
        "name": "东南大学研究生院",
        "homes": ["https://seugs.seu.edu.cn/"],
        "guess": ["https://seugs.seu.edu.cn/"],
    },
    "scu": {
        "name": "四川大学研究生院",
        "homes": [],
        "guess": ["https://yz.scu.edu.cn/"],
    },
    "sdu": {"name": "山东大学研究生院", "homes": [], "guess": ["https://yz.sdu.edu.cn/"]},
    "csu": {"name": "中南大学研究生院", "homes": ["https://gra.csu.edu.cn/"], "guess": []},
    "xjtu": {
        "name": "西安交通大学研究生院",
        "homes": ["https://gs.xjtu.edu.cn/"],
        "guess": ["https://gs.xjtu.edu.cn/tzgg/zsgz.htm"],
    },
    "hit": {"name": "哈尔滨工业大学研究生院", "homes": ["https://hitgs.hit.edu.cn/"], "guess": []},
    "tju": {
        "name": "天津大学研究生院",
        "homes": ["https://gs.tju.edu.cn/"],
        "guess": ["https://gs.tju.edu.cn/"],
    },
    "xmu": {
        "name": "厦门大学研究生院",
        "homes": ["https://yjsy.xmu.edu.cn/", "https://gs.xmu.edu.cn/"],
        "guess": [],
    },
    "cqu": {
        "name": "重庆大学研究生院",
        "homes": ["https://yjs.cqu.edu.cn/"],
        "guess": ["https://yz.cqu.edu.cn/"],
    },
}

    # 栏目链接文本特征（首页自动发现用）已在 _discover_sections 内联

# ===== Top50 扩展候选（2026-09-05 傍晚批）：URL 为研究生院/研招办官方 edu.cn 站 =====
# DNS 或路径错误会被抓取判定自然淘汰（verdict=NO_LIST），如实记录不硬凑。
CANDIDATE_SCHOOLS.update(
    {
        "tsinghua": {"name": "清华大学研究生院", "homes": ["https://yjsy.tsinghua.edu.cn/"], "guess": []},
        "pku": {"name": "北京大学研究生院", "homes": ["https://grs.pku.edu.cn/"], "guess": []},
        "fudan": {"name": "复旦大学研究生院", "homes": ["https://gs.fudan.edu.cn/"], "guess": []},
        "sjtu": {"name": "上海交通大学研究生院", "homes": ["https://yss.sjtu.edu.cn/", "https://yzb.sjtu.edu.cn/"], "guess": []},
        "zju": {"name": "浙江大学研究生院", "homes": ["http://www.grs.zju.edu.cn/"], "guess": []},
        "tongji": {"name": "同济大学研究生院", "homes": ["https://gs.tongji.edu.cn/"], "guess": []},
        "buaa": {"name": "北京航空航天大学研究生院", "homes": ["https://gra.buaa.edu.cn/"], "guess": []},
        "bit": {"name": "北京理工大学研究生院", "homes": ["https://grd.bit.edu.cn/"], "guess": []},
        "ruc": {"name": "中国人民大学研究生院", "homes": ["https://grs.ruc.edu.cn/"], "guess": []},
        "bnu": {"name": "北京师范大学研究生院", "homes": ["https://grad.bnu.edu.cn/"], "guess": []},
        "ecnu": {"name": "华东师范大学研究生院", "homes": ["https://yjsy.ecnu.edu.cn/"], "guess": []},
        "scut": {"name": "华南理工大学研究生院", "homes": ["https://gs.scut.edu.cn/"], "guess": []},
        "hnu": {"name": "湖南大学研究生院", "homes": ["http://gra.hnu.edu.cn/"], "guess": []},
        "lzu": {"name": "兰州大学研究生院", "homes": ["https://ge.lzu.edu.cn/"], "guess": []},
        "jlu": {"name": "吉林大学研究生院", "homes": ["http://yjsy.jlu.edu.cn/"], "guess": []},
        "dlut": {"name": "大连理工大学研究生院", "homes": ["http://gs.dlut.edu.cn/"], "guess": []},
        "uestc": {"name": "电子科技大学研究生院", "homes": ["https://gr.uestc.edu.cn/"], "guess": ["https://gr.uestc.edu.cn/tongzhi/118"]},
        "zzu": {"name": "郑州大学研究生院", "homes": ["http://yz.zzu.edu.cn/"], "guess": []},
        "njust": {"name": "南京理工大学研究生院", "homes": ["http://gs.njust.edu.cn/"], "guess": []},
        "nwpu": {"name": "西北工业大学研究生院", "homes": ["https://gs.nwpu.edu.cn/"], "guess": []},
        "ecust": {"name": "华东理工大学研究生院", "homes": ["https://yjszs.ecust.edu.cn/"], "guess": []},
        "ccnu": {"name": "华中师范大学研究生院", "homes": ["https://gs.ccnu.edu.cn/"], "guess": []},
    }
)


def _discover_sections(crawler: OfficialAnnounceCrawler, home_url: str) -> list[str]:
    """从首页发现候选栏目页：同校 edu.cn 域内、文本含 硕士/招生/通知公告 的链接。"""
    import re

    try:
        resp = crawler._request(home_url)
        resp.encoding = "utf-8"
        html = resp.text
    except Exception as e:
        print(f"    [首页抓取失败] {home_url} | {e}")
        return []
    base_host = (urlparse(home_url).hostname or "").lower()
    base_site = ".".join(base_host.split(".")[-3:]) if base_host.count(".") >= 2 else base_host

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if not re.search(r"硕士招生|招生工作|通知公告|招生信息|招生动态", text or ""):
            continue
        url = urljoin(home_url, a["href"].strip())
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host.endswith(".edu.cn") or not base_site in host:
            continue  # 只跟同校 edu.cn 域
        if url.rstrip("/") not in seen:
            seen.add(url.rstrip("/"))
            found.append(url)
    return found[:6]


def _judge_list(crawler, url: str) -> dict:
    """抓列表页并双模板判定：generic 与 boda 择优（取通过线中新鲜条目多者）。

    模板指纹的落点：.cms 字段直接产出 DEFAULT_SECTIONS 需要的适配器选择，
    每校不再需要人工判断用哪个解析器。
    """
    try:
        resp = crawler._request(url)
        resp.encoding = "utf-8"
        html = resp.text
    except Exception as e:
        return {"url": url, "ok": False, "reason": f"抓取失败: {e}"}

    best: dict | None = None
    for cms in ("generic", "boda"):
        try:
            if cms == "boda":
                entries = _parse_list_entries(html, cms, url)
            else:
                entries = parse_list_generic(html, url)
        except Exception:
            entries = []
        fresh = [e for e in entries if e["date"] >= CUTOFF]
        same_host = all(
            (urlparse(e["url"]).hostname or "").lower() == (urlparse(url).hostname or "").lower()
            for e in entries
        )
        ok = len(entries) >= MIN_ENTRIES and fresh and same_host
        cand = {
            "url": url,
            "ok": ok,
            "cms": cms,
            "n_entries": len(entries),
            "n_fresh": len(fresh),
            "same_host": same_host,
            "newest": entries[0]["date"] if entries else "",
            "sample_urls": [e["url"] for e in entries[:3]],
            "titles": [e["title"][:30] for e in entries[:3]],
            "html": html,
        }
        if best is None or (cand["ok"], cand["n_fresh"]) > (best["ok"], best["n_fresh"]):
            best = cand
    return best


def _judge_details(crawler, urls: list[str]) -> list[dict]:
    """抓 1-2 个详情页验证 extract_main_text ≥80 字。"""
    results = []
    for u in urls[:2]:
        try:
            resp = crawler._request(u)
            resp.encoding = "utf-8"
            html = resp.text
        except Exception as e:
            results.append({"url": u, "ok": False, "reason": f"抓取失败: {e}"})
            continue
        text = extract_main_text(html)
        results.append({"url": u, "ok": len(text) >= MIN_DETAIL_LEN, "len": len(text)})
    return results


def calibrate(key: str, save: bool, force_fetch: bool) -> dict:
    school = CANDIDATE_SCHOOLS[key]
    print(f"\n=== {school['name']} ({key}) ===")
    crawler = OfficialAnnounceCrawler(config={"rate_limit": 2.0, "fetch_detail": False})
    report: dict = {"key": key, "name": school["name"], "lists": []}

    # 候选栏目 = 静态猜测 + 各首页候选的自动发现
    candidates = list(dict.fromkeys(school["guess"]))
    if not force_fetch:
        for home in school["homes"]:
            candidates += _discover_sections(crawler, home)
        # 猜测/首页本身也可直接是达标列表页（如首页即通知公告聚合）
        candidates += list(school["homes"])
    candidates = list(dict.fromkeys(candidates))[:8]
    print(f"  候选栏目 {len(candidates)} 个")

    best: dict | None = None
    for url in candidates:
        r = _judge_list(crawler, url)
        r.pop("html", None)
        print(
            f"  [{ 'OK' if r['ok'] else '--' }] {url} | 模板={r.get('cms', '-')}"
            f" 条数={r.get('n_entries', 0)}"
            f" 新鲜={r.get('n_fresh', 0)} 最新={r.get('newest', '-')}"
        )
        report["lists"].append(r)
        if r["ok"] and (best is None or r["n_fresh"] > best["n_fresh"]):
            best = dict(r)

    if best:
        # 重抓最佳栏目留 HTML，验证详情页
        resp = crawler._request(best["url"])
        resp.encoding = "utf-8"
        best_html = resp.text
        entries = parse_list_generic(best_html, best["url"])
        details = _judge_details(crawler, [e["url"] for e in entries])
        det_ok = [d for d in details if d.get("ok")]
        print(
            f"  详情验证: {len(det_ok)}/{len(details)} 达标 "
            f"({[d.get('len') for d in details]})"
        )
        report["best_list"] = {k: v for k, v in best.items()}
        report["details"] = details
        if det_ok:
            report["verdict"] = "PASS"
            sec_name = school["name"]
            if not sec_name.endswith(("公告", "通知", "动态", "信息")):
                sec_name += "通知公告"
            report["section"] = {
                "name": sec_name,
                "list_url": best["url"],
                "cms": best["cms"],
                "content_cls": "",
            }
            if save:
                FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
                list_path = FIXTURE_DIR / f"{key}_list.html"
                list_path.write_text(best_html, encoding="utf-8")
                det_url = det_ok[0]["url"]
                dresp = crawler._request(det_url)
                dresp.encoding = "utf-8"
                (FIXTURE_DIR / f"{key}_detail.html").write_text(dresp.text, encoding="utf-8")
                print(f"  夹具已存: {list_path.name} + {key}_detail.html")
                entries_out = [
                    {"url": e["url"], "title": e["title"], "date": e["date"]} for e in entries
                ]
                (FIXTURE_DIR / f"{key}_calibration.json").write_text(
                    json.dumps(
                        {"list_url": best["url"], "detail_url": det_url, "entries": entries_out},
                        ensure_ascii=False,
                        indent=1,
                    ),
                    encoding="utf-8",
                )
        else:
            report["verdict"] = "DETAIL_FAIL"
    else:
        report["verdict"] = "NO_LIST"
        print("  无达标栏目")

    return report


def main():
    parser = argparse.ArgumentParser(description="official_announce 扩校标定")
    parser.add_argument("schools", nargs="*", help="校拼音 key（whu hust nju seu scu sdu csu xjtu hit tju xmu cqu）")
    parser.add_argument("--all", action="store_true", help="标定全部候选校")
    parser.add_argument("--save", action="store_true", help="达标校存夹具到 tests/fixtures/official_announce/")
    parser.add_argument(
        "--force-fetch", action="store_true", help="跳过首页自动发现（省请求，只用静态候选）"
    )
    args = parser.parse_args()
    keys = list(CANDIDATE_SCHOOLS) if args.all else args.schools
    if not keys:
        parser.error("指定校 key 或 --all")
    print(f"标定 {len(keys)} 校（限速 2s/请求，robots+SSRF 护栏开启）")
    out = {}
    for k in keys:
        try:
            out[k] = calibrate(k, args.save, args.force_fetch)
        except Exception as e:
            print(f"  [异常] {k}: {e}")
            out[k] = {"key": k, "verdict": "ERROR", "reason": str(e)}
    verdicts = {k: v.get("verdict") for k, v in out.items()}
    print("\n===== 结论 =====")
    for k, v in verdicts.items():
        print(f"  {k}: {v}")
    passed = [k for k, v in verdicts.items() if v == "PASS"]
    print(f"达标 {len(passed)}/{len(keys)}: {passed}")
    sections = [v["section"] for v in out.values() if v.get("section")]
    if sections:
        print("\n===== PASS 校 DEFAULT_SECTIONS 条目（可直接粘贴） =====")
        print(json.dumps(sections, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
