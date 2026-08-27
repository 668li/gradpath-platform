"""职位粒度薪资入库（2026-08-16）：上海人社局工资价位 → salary_benchmarks。

数据源：salary_gov_data.json 中 indicator=="长三角一体化示范区制造业企业市场工资价位"
的 85 个职位 × 5 个分位数（10/25/50/75/90%，元/年），2024 年口径。

映射（如实标注口径，不伪造）：
  - 每职位一行：salary_min=P10、salary_median=P50、salary_max=P90（缺档取最近可用分位）
  - company="长三角示范区市场价位（制造业）"——数据口径名（市场基准价，非特定公司）
  - experience_level="mid"——市场价位覆盖全经验段，取中位代表口径（source 注明）
  - source="上海市人社局2024工资价位"（完整官方链接见 market_data 同源行）

幂等：(position, year, company) 去重。全 ORM 参数绑定。
"""

import json
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark

DATA_FILE = BACKEND_ROOT / "app" / "crawlers" / "real_data" / "salary_gov_data.json"
INDICATOR = "长三角一体化示范区制造业企业市场工资价位"
COMPANY_LABEL = "长三角示范区市场价位（制造业）"
SOURCE_LABEL = "上海市人社局2024工资价位"


def main() -> None:
    rows = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    buckets: dict[tuple, dict[int, float]] = {}
    for r in rows:
        if r.get("indicator") != INDICATOR:
            continue
        m = re.match(r"(.+?)\((\d+)%分位数\)", str(r.get("category") or ""))
        if not m:
            continue
        position, pct = m.group(1).strip(), int(m.group(2))
        year = int(r.get("year"))
        value = r.get("value")
        if value is None:
            continue
        buckets.setdefault((position, year), {})[pct] = float(value)

    inserted = duplicated = 0
    with SessionLocal() as db:
        for (position, year), pcts in buckets.items():
            exists = (
                db.query(SalaryBenchmark.id)
                .filter(
                    SalaryBenchmark.position == position,
                    SalaryBenchmark.year == year,
                    SalaryBenchmark.company == COMPANY_LABEL,
                )
                .first()
            )
            if exists:
                duplicated += 1
                continue

            # 取分位：优先 10/50/90，缺档用最近档
            def pick(prefer: list[int]) -> int:
                for p in prefer:
                    if p in pcts:
                        return int(round(pcts[p]))
                return int(round(pcts[max(pcts)]))

            db.add(
                SalaryBenchmark(
                    company=COMPANY_LABEL,
                    position=position[:200],
                    city="长三角一体化示范区",
                    experience_level=ExperienceLevel.mid,
                    salary_min=pick([10, 25, 50]),
                    salary_median=pick([50, 25, 75]),
                    salary_max=pick([90, 75, 50]),
                    source=SOURCE_LABEL,
                    year=year,
                )
            )
            inserted += 1
        db.commit()
        total = db.query(SalaryBenchmark).count()
    print(f"入库 {inserted} 条职位价位 / 重复 {duplicated} | salary_benchmarks 总数: {total}")


if __name__ == "__main__":
    main()
