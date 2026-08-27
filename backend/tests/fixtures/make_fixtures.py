# backend/tests/fixtures/make_fixtures.py
"""生成 tests/fixtures/real_data/ 下的真实数据样本夹具。

从本地完整抓取数据（app/crawlers/real_data/*.json，不入库）采样真实记录，
供 CI 在没有本地抓取快照时运行种子与导入相关测试。样本即真实记录，非合成。

采样策略：
- 测试断言引用的筛选组合（如"自动化测试工程师"）整段保留；
- 其余配额在全文件范围内均匀步进取样，保证公司/岗位/城市多样性。

用法：py -3.13 backend/tests/fixtures/make_fixtures.py
"""

import json
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[2] / "app" / "crawlers" / "real_data"
DST = pathlib.Path(__file__).resolve().parent / "real_data"

# 每个文件的目标条数：足够测试断言（过滤/分页/幂等/多样性），不膨胀仓库
LIMITS = {
    "salary_real.json": 400,
    "salary_expand.json": 400,
    "bilibili_expand.json": 10,
}


def _test_referenced(rec: dict) -> bool:
    """测试断言引用的具体筛选值必须出现在样本里。"""
    return rec.get("position") == "自动化测试工程师"


def build_sample(raw: list[dict], limit: int) -> list[dict]:
    picked: list[dict] = []
    seen: set[str] = set()

    def add(rec: dict) -> None:
        key = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            picked.append(rec)

    # 先收测试引用的组合（封顶一半配额）
    for rec in raw:
        if _test_referenced(rec):
            add(rec)
            if len(picked) >= limit // 2:
                break
    # 再全文件均匀步进补齐多样性
    remaining = max(1, limit - len(picked))
    step = max(1, len(raw) // remaining)
    for rec in raw[::step]:
        add(rec)
        if len(picked) >= limit:
            break
    return picked[:limit]


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    for name, limit in LIMITS.items():
        raw = json.loads((SRC / name).read_text(encoding="utf-8-sig"))
        sample = build_sample(raw, limit)
        out = DST / name
        out.write_text(
            json.dumps(sample, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        print(f"{name}: {len(raw)} -> {len(sample)} 条 -> {out}")


if __name__ == "__main__":
    main()
