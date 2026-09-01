"""官方公告并发冒烟测试：验证并发 fetch() 线程安全 + 与串行结果对齐。

复用 OfficialAnnounceCrawler 的真实 _request（SSRF/robots/限速护栏），
只做内存 fetch（不 store，不动 DB）。断言并发(2)抓到的条目数与
串行(1)完全一致 → 证明并行走同一 _request 路径、无丢统计/无竞态。

用法（本地）:
    py -3.13 scripts/smoke_official_concurrency.py [--concurrency 2]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crawlers.research.official_announce_crawler import (
    DEFAULT_SECTIONS,
    OfficialAnnounceCrawler,
)


def run(concurrency: int) -> list[dict]:
    crawler = OfficialAnnounceCrawler(
        config={"concurrency": concurrency, "fetch_detail": False, "rate_limit": 0.3}
    )
    items = crawler.fetch()
    urls = sorted(i["url"] for i in items)
    print(
        f"[并发={concurrency}] 抓取 {len(items)} 条 | errors={crawler.stats['errors']} "
        f"| 来源={sorted(set(i['source_name'] for i in items))}"
    )
    return urls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()

    if len(DEFAULT_SECTIONS) < 2:
        print(f"默认栏目不足 2 个（{len(DEFAULT_SECTIONS)}），无法对比并发/串行")
        return

    serial = run(1)
    concurrent = run(args.concurrency)

    if serial == concurrent:
        print(f"PASS 并发={args.concurrency} 与串行结果完全一致（{len(serial)} 条）")
    else:
        only_serial = set(serial) - set(concurrent)
        only_conc = set(concurrent) - set(serial)
        print(f"FAIL 并发={args.concurrency} 与串行不一致")
        print(f"  仅串行有: {only_serial}")
        print(f"  仅并发有: {only_conc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
