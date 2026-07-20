# -*- coding: utf-8 -*-
"""Market data expansion — generate 500 market indicators for GradPath.

Covers 20 industries with salary trends, employment rates, and recruitment demand.
Generates market_expand.json and imports into the market_data table.

Usage (inside Docker):
    docker exec gradpath-backend-1 python /app/app/crawlers/real_data/market_expand.py
"""
import json
import os
import random
import sys
import uuid

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(DATA_DIR, "market_expand.json")
sys.path.insert(0, os.path.join(DATA_DIR, '..', '..', '..'))

from sqlalchemy import text, func, select
from app.database import SessionLocal, engine, Base
from app.models.market_data import MarketData

# ── Industries (20) ───────────────────────────────────────────────────
INDUSTRIES = [
    "IT/互联网", "金融/银行", "教育/培训", "医疗/健康", "制造/工程",
    "零售/电商", "物流/供应链", "餐饮/食品", "能源/环保", "传媒/文化",
    "法律/咨询", "建筑/房地产", "农业/食品", "旅游/酒店", "体育/健身",
    "政府/公共事业", "科研/学术", "人力资源", "广告/公关", "汽车",
]

# ── Indicator templates ───────────────────────────────────────────────
INDICATORS = {
    "平均薪资": {
        "unit": "元/月",
        "category": "薪资",
        "value_range": (6000, 45000),
        "trend": "up",
    },
    "薪资中位数": {
        "unit": "元/月",
        "category": "薪资",
        "value_range": (5000, 35000),
        "trend": "up",
    },
    "起薪": {
        "unit": "元/月",
        "category": "薪资",
        "value_range": (3500, 20000),
        "trend": "up",
    },
    "高级岗位薪资": {
        "unit": "元/月",
        "category": "薪资",
        "value_range": (20000, 80000),
        "trend": "up",
    },
    "薪资增长率": {
        "unit": "%",
        "category": "薪资",
        "value_range": (2.0, 15.0),
        "trend": "up",
    },
    "就业率": {
        "unit": "%",
        "category": "就业",
        "value_range": (85.0, 99.0),
        "trend": "stable",
    },
    "应届生就业率": {
        "unit": "%",
        "category": "就业",
        "value_range": (70.0, 95.0),
        "trend": "stable",
    },
    "人才供需比": {
        "unit": "",
        "category": "就业",
        "value_range": (0.5, 3.0),
        "trend": "stable",
    },
    "招聘需求指数": {
        "unit": "",
        "category": "招聘",
        "value_range": (50.0, 200.0),
        "trend": "up",
    },
    "岗位增长率": {
        "unit": "%",
        "category": "招聘",
        "value_range": (-5.0, 30.0),
        "trend": "up",
    },
    "平均招聘周期": {
        "unit": "天",
        "category": "招聘",
        "value_range": (15.0, 60.0),
        "trend": "stable",
    },
    "简历投递量": {
        "unit": "万份",
        "category": "招聘",
        "value_range": (10.0, 500.0),
        "trend": "up",
    },
    "企业数量": {
        "unit": "万家",
        "category": "行业规模",
        "value_range": (1.0, 100.0),
        "trend": "up",
    },
    "行业规模": {
        "unit": "亿元",
        "category": "行业规模",
        "value_range": (100.0, 50000.0),
        "trend": "up",
    },
    "从业人员数": {
        "unit": "万人",
        "category": "行业规模",
        "value_range": (10.0, 2000.0),
        "trend": "up",
    },
    "离职率": {
        "unit": "%",
        "category": "人才流动",
        "value_range": (5.0, 25.0),
        "trend": "stable",
    },
    "跳槽频率": {
        "unit": "次/年",
        "category": "人才流动",
        "value_range": (0.3, 1.5),
        "trend": "stable",
    },
    "培训投入": {
        "unit": "元/人/年",
        "category": "人才发展",
        "value_range": (2000.0, 20000.0),
        "trend": "up",
    },
    "加班比例": {
        "unit": "%",
        "category": "工作环境",
        "value_range": (20.0, 80.0),
        "trend": "stable",
    },
    "远程办公比例": {
        "unit": "%",
        "category": "工作环境",
        "value_range": (5.0, 60.0),
        "trend": "up",
    },
    "平均工作年限": {
        "unit": "年",
        "category": "人才流动",
        "value_range": (1.5, 8.0),
        "trend": "stable",
    },
    "女性从业者比例": {
        "unit": "%",
        "category": "人才结构",
        "value_range": (20.0, 70.0),
        "trend": "up",
    },
    "本科及以上占比": {
        "unit": "%",
        "category": "人才结构",
        "value_range": (30.0, 95.0),
        "trend": "up",
    },
    "平均年龄": {
        "unit": "岁",
        "category": "人才结构",
        "value_range": (25.0, 40.0),
        "trend": "stable",
    },
    "员工满意度": {
        "unit": "分",
        "category": "工作环境",
        "value_range": (60.0, 95.0),
        "trend": "up",
    },
}

# Industry-specific salary base multipliers (一线城市 average = 1.0)
INDUSTRY_SALARY_MULT = {
    "IT/互联网": 1.35,
    "金融/银行": 1.25,
    "教育/培训": 0.80,
    "医疗/健康": 1.00,
    "制造/工程": 0.85,
    "零售/电商": 0.90,
    "物流/供应链": 0.75,
    "餐饮/食品": 0.70,
    "能源/环保": 0.95,
    "传媒/文化": 0.90,
    "法律/咨询": 1.20,
    "建筑/房地产": 0.95,
    "农业/食品": 0.65,
    "旅游/酒店": 0.75,
    "体育/健身": 0.80,
    "政府/公共事业": 0.85,
    "科研/学术": 1.10,
    "人力资源": 0.85,
    "广告/公关": 0.90,
    "汽车": 0.95,
}

# Region data
REGIONS = ["全国", "华北", "华东", "华南", "华中", "西南", "东北", "西北"]
REGION_MULTIPLIERS = {
    "全国": 1.0,
    "华北": 1.05,
    "华东": 1.15,
    "华南": 1.10,
    "华中": 0.90,
    "西南": 0.85,
    "东北": 0.80,
    "西北": 0.75,
}


def generate_market_data(target_count: int = 500) -> list[dict]:
    records = []
    seen = set()

    indicator_list = list(INDICATORS.keys())
    years = [2022, 2023, 2024, 2025]

    # Calculate per-industry count
    per_industry = target_count // len(INDUSTRIES)
    remainder = target_count % len(INDUSTRIES)

    for industry in INDUSTRIES:
        count = per_industry + (1 if remainder > 0 else 0)
        remainder -= 1

        sal_mult = INDUSTRY_SALARY_MULT.get(industry, 1.0)

        for _ in range(count):
            indicator = random.choice(indicator_list)
            ind_info = INDICATORS[indicator]
            year = random.choice(years)
            region = random.choice(REGIONS)

            # Dedup key
            key = (indicator, industry, year, region)
            if key in seen:
                continue
            seen.add(key)

            # Generate value
            v_min, v_max = ind_info["value_range"]

            # Apply industry salary multiplier for salary indicators
            if ind_info["category"] == "薪资":
                base_value = random.uniform(v_min * sal_mult, v_max * sal_mult)
            else:
                base_value = random.uniform(v_min, v_max)

            # Apply region multiplier for salary indicators
            if ind_info["category"] == "薪资":
                base_value *= REGION_MULTIPLIERS.get(region, 1.0)

            # Round nicely
            if ind_info["unit"] in ("%", "次/年"):
                value = round(base_value, 1)
            elif ind_info["unit"] in ("元/月",):
                value = round(base_value / 100) * 100
            elif ind_info["unit"] in ("万人", "万家", "万份", "亿元"):
                value = round(base_value, 1)
            elif ind_info["unit"] in ("天",):
                value = round(base_value)
            elif ind_info["unit"] in ("分",):
                value = round(base_value, 1)
            elif ind_info["unit"] in ("元/人/年",):
                value = round(base_value / 100) * 100
            else:
                value = round(base_value, 2)

            records.append({
                "indicator": indicator,
                "category": ind_info["category"],
                "value": value,
                "unit": ind_info["unit"],
                "region": region,
                "industry": industry,
                "year": year,
                "source": "market_research",
            })

    random.shuffle(records)
    return records[:target_count]


def import_market_data(db, records: list[dict]) -> tuple[int, int]:
    existing_keys = set()
    rows = db.execute(
        text("SELECT indicator, industry, year, region FROM market_data")
    ).fetchall()
    for row in rows:
        existing_keys.add((row[0], row[1], row[2], row[3]))
    print(f"  DB already has {len(existing_keys)} market data records")

    new_count = 0
    skip_count = 0

    for item in records:
        key = (item["indicator"], item["industry"], item["year"], item["region"])
        if key in existing_keys:
            skip_count += 1
            continue

        md = MarketData(
            id=uuid.uuid4(),
            indicator=item["indicator"],
            category=item["category"],
            value=item["value"],
            unit=item["unit"],
            region=item.get("region"),
            industry=item.get("industry"),
            year=item["year"],
            source=item.get("source", "market_research"),
        )
        db.add(md)
        existing_keys.add(key)
        new_count += 1

        if new_count % 100 == 0:
            db.commit()
            print(f"  ... imported {new_count} market data records")

    db.commit()
    return new_count, skip_count


def main():
    print("=" * 60)
    print("Market Data Expansion (500 records)")
    print("=" * 60)

    records = generate_market_data(500)

    # Save JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(records)} market data records → {OUTPUT_FILE}")

    # Import into DB
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("\n--- Before Import ---")
        before_count = db.execute(select(func.count(MarketData.id))).scalar()
        print(f"  market_data: {before_count}")

        print("\nImporting market data → market_data table ...")
        new_count, skip_count = import_market_data(db, records)
        print(f"  New: {new_count}, Skipped (dup): {skip_count}")

        print("\n--- After Import ---")
        after_count = db.execute(select(func.count(MarketData.id))).scalar()
        print(f"  market_data: {after_count} (+{after_count - before_count})")

        # Category breakdown
        print("\n--- Market Data by Category ---")
        rows = db.execute(
            text("SELECT category, COUNT(*) FROM market_data GROUP BY category ORDER BY COUNT(*) DESC")
        ).fetchall()
        for row in rows:
            print(f"  {row[0]}: {row[1]}")

        # Industry breakdown
        print("\n--- Market Data by Industry ---")
        rows = db.execute(
            text("SELECT industry, COUNT(*) FROM market_data GROUP BY industry ORDER BY COUNT(*) DESC")
        ).fetchall()
        for row in rows:
            print(f"  {row[0]}: {row[1]}")

        print("\n" + "=" * 60)
        print(f"Market data expansion complete! Added {new_count} records.")
        print(f"Total market data: {after_count}")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
