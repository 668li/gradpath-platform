"""统计公报就业面数据入库（2026-08-16）：stats_gongbao_data.json → market_data 表。

杠杆化 #4：国家统计局年度统计公报文本抽取的宏观就业面指标
（就业人员/城镇新增就业/调查失业率/农民工/可支配收入，2022-2025 四年序列）。
幂等键 (indicator, category, year, region, industry) 与 import_salary_gov_market 一致；
纯增量追加（不动既有工资数据，不删除任何行）。全 ORM 参数绑定。
"""
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.market_data import MarketData

DATA_FILE = BACKEND_ROOT / "app" / "crawlers" / "real_data" / "stats_gongbao_data.json"


def load_source_rows():
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def main() -> None:
    rows = load_source_rows()
    with SessionLocal() as db:
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
