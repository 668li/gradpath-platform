"""职位粒度薪资入库·二批（2026-08-16）：salary_position_data.json → salary_benchmarks。

数据源（agent 采集，3 城人社局公开公告 PDF）：广州 480 + 深圳 302（含分学历×工龄 33）
+ 杭州 264 = 1046 条，10%/50%/90% 分位 → min/median/max，对照原文抽查通过。

映射要点：
  - JSON 无 company（政府市场水平数据）→ company = "{city}人社局市场价位"（数据口径名）
  - experience_level 为中文工龄档 → 映射 SalaryBenchmark.ExperienceLevel：
    1年以下→entry、2-3年→junior、4-5年→mid、6-10年→senior、11年以上→lead、
    不限/职业细类行→mid（市场全档代表口径，source 注明）
  - 深圳「分学历」行 position 为学历名（如"大学本科"），保留原样便于学历价位检索
  - source（String 50）：源机构+调查期，完整 URL 见 source_url 字段留档于 JSON

幂等：(position, city, year, company) 去重。全 ORM 参数绑定。
"""
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark

DATA_FILE = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else BACKEND_ROOT / "app" / "crawlers" / "real_data" / "salary_position_data.json"
)

EXP_MAP = {
    "1年以下": ExperienceLevel.entry,
    "2-3年": ExperienceLevel.junior,
    "4-5年": ExperienceLevel.mid,
    "6-10年": ExperienceLevel.senior,
    "11年以上": ExperienceLevel.lead,
}


def main() -> None:
    rows = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    inserted = duplicated = skipped = 0
    with SessionLocal() as db:
        for r in rows:
            position = str(r.get("position") or "").strip()[:200]
            city = str(r.get("city") or "").strip()[:50]
            year = r.get("year")
            smn, smd, smx = r.get("salary_min"), r.get("salary_median"), r.get("salary_max")
            if not position or not city or not year or smn is None or smd is None or smx is None:
                skipped += 1
                continue
            company = f"{city}人社局市场价位"
            exists = (
                db.query(SalaryBenchmark.id)
                .filter(
                    SalaryBenchmark.position == position,
                    SalaryBenchmark.city == city,
                    SalaryBenchmark.year == int(year),
                    SalaryBenchmark.company == company,
                )
                .first()
            )
            if exists:
                duplicated += 1
                continue
            exp_raw = str(r.get("experience_level") or "").strip()
            exp = EXP_MAP.get(exp_raw, ExperienceLevel.mid)
            source = str(r.get("source") or "人社局公开公告").strip()[:50]
            db.add(
                SalaryBenchmark(
                    company=company,
                    position=position,
                    city=city,
                    experience_level=exp,
                    salary_min=int(smn),
                    salary_median=int(smd),
                    salary_max=int(smx),
                    source=source,
                    year=int(year),
                )
            )
            inserted += 1
        db.commit()
        total = db.query(SalaryBenchmark).count()
    print(f"入库 {inserted} 条 / 重复 {duplicated} / 无效跳过 {skipped} | salary_benchmarks 总数: {total}")


if __name__ == "__main__":
    main()
