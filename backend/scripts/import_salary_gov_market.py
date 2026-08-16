"""政府公开薪资数据入库（2026-08-16）：salary_gov_data.json → market_data 表。

背景：market_data 原 41 条为合成模仿数据（market_expand.json 生成），
salary_benchmarks 原 2880 条合成已删。本脚本：
  1) 备份并清空现有 market_data（合成数据，归档可追溯）
  2) 导入 agent 采集的 1185 条真实政府公开薪资（国家统计局 749 + 上海人社局 436），
     每条带 source_url 官方公告链接

消费方：AI 决策建议（decision_advice_service）等。幂等：重跑时按
(indicator, category, year, region, industry) 去重跳过。全 ORM 参数绑定。
"""
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.market_data import MarketData

DATA_FILE = BACKEND_ROOT / "app" / "crawlers" / "real_data" / "salary_gov_data.json"
ARCHIVE_DIR = BACKEND_ROOT / "scripts" / "archive" / "synthetic_purge_2026-08-16"


def load_source_rows():
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def dump_backup(rows):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    target = ARCHIVE_DIR / "market_data.json"
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    rows = load_source_rows()
    with SessionLocal() as db:
        # 1) 备份并清空合成数据
        existing = db.query(MarketData).all()
        if existing and any(not m.source_url for m in existing):
            backup = []
            for m in existing:
                item = {}
                for col in MarketData.__table__.columns.keys():
                    v = getattr(m, col)
                    if v is not None and not isinstance(v, (int, float, bool, str)):
                        v = str(v)
                    item[col] = v
                backup.append(item)
            dump_backup(backup)
            n = db.query(MarketData).delete()
            print(f"已备份并删除合成 market_data: {n} 条")

        # 2) 导入真实数据（幂等去重）
        inserted = duplicated = skipped = 0
        for r in rows:
            indicator = str(r.get("indicator") or "").strip()[:100]
            category = str(r.get("category") or "").strip()[:50]
            value = r.get("value")
            year = r.get("year")
            if not indicator or not category or value is None or not year:
                skipped += 1
                continue
            region = str(r.get("region") or "").strip()[:50] or None
            industry = str(r.get("industry") or "").strip()[:50] or None
            exists = (
                db.query(MarketData.id)
                .filter(
                    MarketData.indicator == indicator,
                    MarketData.category == category,
                    MarketData.year == int(year),
                    MarketData.region.is_(None) if region is None else MarketData.region == region,
                    MarketData.industry.is_(None) if industry is None else MarketData.industry == industry,
                )
                .first()
            )
            if exists:
                duplicated += 1
                continue
            db.add(
                MarketData(
                    indicator=indicator,
                    category=category,
                    value=float(value),
                    unit=str(r.get("unit") or "")[:20],
                    region=region,
                    industry=industry,
                    year=int(year),
                    source=str(r.get("source") or "")[:100],
                    source_url=str(r.get("source_url") or "") or None,
                )
            )
            inserted += 1
        db.commit()
        total = db.query(MarketData).count()
    print(f"导入 {inserted} 条 / 重复 {duplicated} / 无效跳过 {skipped} | market_data 总数: {total}")


if __name__ == "__main__":
    main()
