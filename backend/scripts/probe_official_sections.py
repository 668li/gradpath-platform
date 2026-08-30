"""探测候选高校研招公告列表页是否匹配博达 CMS 模板（_LIST_ITEM_RE）。

复用 OfficialAnnounceCrawler 的 _request（自带 SSRF 校验/robots 护栏），
匹配成功的候选才可追加进 official_announce_crawler.DEFAULT_SECTIONS。

用法（本地）:
    py -3.13 scripts/probe_official_sections.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crawlers.research.official_announce_crawler import (
    _LIST_ITEM_RE as LIST_RE,
    OfficialAnnounceCrawler,
)

CANDIDATES = [
    ("华中农业大学研究生院硕士招生", "https://yjs.hzau.edu.cn/zsgz/sszs.htm"),
    ("华中师范大学研究生院招生信息", "https://yjs.ccnu.edu.cn/zsgz/zsxx.htm"),
    ("西北农林科技大学研究生院招生", "https://yz.nwafu.edu.cn/zsgz/sszs.htm"),
    ("南京农业大学研究生院招生工作", "https://yjsy.njau.edu.cn/zsgz/sszs.htm"),
    ("华南农业大学研究生院招生", "https://yjsy.scau.edu.cn/zsgz/sszs.htm"),
    ("山东农业大学研究生处招生", "https://yjsc.sdau.edu.cn/zsgz/sszs.htm"),
    ("福建农林大学研究生院招生", "https://yjsy.fafu.edu.cn/zsgz/sszs.htm"),
    ("湖南农业大学研究生院招生", "https://yjsy.hunau.edu.cn/zsgz/sszs.htm"),
    ("四川农业大学研究生院招生", "https://yjs.sicau.edu.cn/zsgz/sszs.htm"),
    ("河北农业大学研究生院招生", "https://yjs.hebau.edu.cn/zsgz/sszs.htm"),
    ("东北农业大学研究生院招生", "https://yjsy.neau.edu.cn/zsgz/sszs.htm"),
    ("安徽农业大学研究生院招生", "https://yjs.ahau.edu.cn/zsgz/sszs.htm"),
    ("江西农业大学研究生院招生", "https://yjsy.jxau.edu.cn/zsgz/sszs.htm"),
    ("河南农业大学研究生院招生", "https://yjs.henau.edu.cn/zsgz/sszs.htm"),
    ("吉林农业大学研究生院招生", "https://yjs.jlau.edu.cn/zsgz/sszs.htm"),
    ("沈阳农业大学研究生院招生", "https://yjsy.syau.edu.cn/zsgz/sszs.htm"),
    ("甘肃农业大学研究生院招生", "https://yjs.gsau.edu.cn/zsgz/sszs.htm"),
    ("云南农业大学研究生处招生", "https://yjs.ynau.edu.cn/zsgz/sszs.htm"),
    ("山西农业大学研究生院招生", "https://yjs.sxau.edu.cn/zsgz/sszs.htm"),
    ("内蒙古农业大学研究生院招生", "https://yjsy.imau.edu.cn/zsgz/sszs.htm"),
    ("北京林业大学研究生院招生", "https://yjsy.bjfu.edu.cn/zsgz/sszs.htm"),
    ("东北林业大学研究生院招生", "https://yjsy.nefu.edu.cn/zsgz/sszs.htm"),
    ("南京林业大学研究生院招生", "https://yjsy.njfu.edu.cn/zsgz/sszs.htm"),
    ("中南林业科技大学研究生院招生", "https://yjsy.csuft.edu.cn/zsgz/sszs.htm"),
    ("浙江农林大学研究生院招生", "https://yjsy.zafu.edu.cn/zsgz/sszs.htm"),
]


def main() -> None:
    crawler = OfficialAnnounceCrawler(config={"fetch_detail": False})
    ok = 0
    for name, url in CANDIDATES:
        try:
            resp = crawler._request(url)
            resp.encoding = "utf-8"
            matches = LIST_RE.findall(resp.text)
            if matches:
                ok += 1
                print(f"MATCH {len(matches):3d}  {name}  {url}")
            else:
                print(f"NOMAT        {name}  {url}")
        except Exception as e:
            print(f"FAIL         {name}  {url}  {type(e).__name__}: {str(e)[:60]}")
    print(f"\n匹配 {ok}/{len(CANDIDATES)}")


if __name__ == "__main__":
    main()
