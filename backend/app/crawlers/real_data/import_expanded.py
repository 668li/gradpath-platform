# -*- coding: utf-8 -*-
"""Import expanded civil service and salary data into GradPath database.

Reads:
  - civil_service_expanded.json → knowledge_articles (category='civil_service')
  - salary_real.json → salary_benchmarks

Usage (inside Docker):
    docker exec gradpath-backend-1 python /app/app/crawlers/real_data/import_expanded.py
"""
import json
import os
import re
import sys
import uuid

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(DATA_DIR, '..', '..', '..'))

from sqlalchemy import text, func, select
from app.database import SessionLocal, engine, Base
from app.models.knowledge_article import KnowledgeArticle
from app.models.salary_benchmark import SalaryBenchmark, ExperienceLevel


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  [SKIP] {filename} not found")
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"  [OK] Loaded {filename}: {len(data) if isinstance(data, list) else 'dict'}")
        return data
    except Exception as e:
        print(f"  [ERROR] {filename}: {e}")
        return None


def clean_content(raw):
    if not raw:
        return ""
    text = re.sub(r'<[^>]+>', ' ', raw)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def import_civil_service_articles(db):
    """Import civil_service_expanded.json → knowledge_articles."""
    data = load_json("civil_service_expanded.json")
    if not data:
        return 0, 0

    # Get existing URLs for dedup
    existing_rows = db.execute(
        text("SELECT metadata->>'url' FROM knowledge_articles WHERE metadata->>'url' IS NOT NULL")
    ).fetchall()
    existing_urls = {row[0] for row in existing_rows if row[0]}
    print(f"  DB already has {len(existing_urls)} articles with URLs")

    new_count = 0
    skip_count = 0
    for item in data:
        url = item.get("url", "")
        if url in existing_urls:
            skip_count += 1
            continue

        title = item.get("title", "")[:200]
        content = clean_content(item.get("content", ""))
        if len(content) < 20:
            content = title

        category = item.get("category", "国考")
        source_name = item.get("source", "offcn")

        ka = KnowledgeArticle(
            id=uuid.uuid4(),
            category="civil_service",
            title=title,
            content=content[:10000],
            tags=["公务员", "公考", category, source_name],
            source=source_name,
            metadata_={
                "url": url,
                "sub_category": category,
                "source_site": source_name,
            },
            is_published=True,
        )
        db.add(ka)
        if url:
            existing_urls.add(url)
        new_count += 1

        if new_count % 100 == 0:
            db.commit()
            print(f"  ... imported {new_count} civil service articles")

    db.commit()
    return new_count, skip_count


def import_salary_benchmarks(db):
    """Import salary_real.json → salary_benchmarks."""
    data = load_json("salary_real.json")
    if not data:
        return 0, 0

    # Build existing dedup set: (company, position, city, experience_level, year)
    existing_rows = db.execute(
        text("SELECT company, position, city, experience_level, year FROM salary_benchmarks")
    ).fetchall()
    existing_keys = {
        (row[0], row[1], row[2], row[3], row[4]) for row in existing_rows
    }
    print(f"  DB already has {len(existing_keys)} salary benchmarks")

    new_count = 0
    skip_count = 0

    # Map string experience level to enum
    exp_map = {
        "entry": ExperienceLevel.entry,
        "junior": ExperienceLevel.junior,
        "mid": ExperienceLevel.mid,
        "senior": ExperienceLevel.senior,
        "lead": ExperienceLevel.lead,
    }

    for item in data:
        company = item.get("company", "")[:200]
        position = item.get("position", "")[:200]
        city = item.get("city", "")[:50]
        exp_str = item.get("experience_level", "entry")
        year = item.get("year", 2025)

        exp_level = exp_map.get(exp_str, ExperienceLevel.entry)

        key = (company, position, city, exp_str, year)
        if key in existing_keys:
            skip_count += 1
            continue

        salary_min = item.get("salary_min", 5000)
        salary_median = item.get("salary_median", 8000)
        salary_max = item.get("salary_max", 12000)

        # Ensure min <= median <= max
        salary_min = max(3000, int(salary_min))
        salary_max = max(salary_min + 1000, int(salary_max))
        salary_median = max(salary_min + 500, min(salary_max - 500, int(salary_median)))

        sb = SalaryBenchmark(
            id=uuid.uuid4(),
            company=company,
            position=position,
            city=city,
            experience_level=exp_level,
            salary_min=salary_min,
            salary_median=salary_median,
            salary_max=salary_max,
            source=item.get("source", "market_research"),
            year=year,
        )
        db.add(sb)
        existing_keys.add(key)
        new_count += 1

        if new_count % 200 == 0:
            db.commit()
            print(f"  ... imported {new_count} salary benchmarks")

    db.commit()
    return new_count, skip_count


def verify_counts(db):
    """Get current row counts for relevant tables."""
    ka_count = db.execute(select(func.count(KnowledgeArticle.id))).scalar()
    sb_count = db.execute(select(func.count(SalaryBenchmark.id))).scalar()
    return {"knowledge_articles": ka_count, "salary_benchmarks": sb_count}


def main():
    from sqlalchemy import select

    print("=" * 60)
    print("GradPath Expanded Data Import")
    print("=" * 60)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Before counts
        print("\n--- Before Import ---")
        before = verify_counts(db)
        for name, count in before.items():
            print(f"  {name}: {count}")

        # 1. Import civil service articles
        print("\n[1/2] Importing civil_service_expanded.json → knowledge_articles ...")
        cs_new, cs_skip = import_civil_service_articles(db)
        print(f"  New: {cs_new}, Skipped (dup): {cs_skip}")

        # 2. Import salary benchmarks
        print("\n[2/2] Importing salary_real.json → salary_benchmarks ...")
        sb_new, sb_skip = import_salary_benchmarks(db)
        print(f"  New: {sb_new}, Skipped (dup): {sb_skip}")

        # After counts
        print("\n--- After Import ---")
        after = verify_counts(db)
        for name, count in after.items():
            delta = count - before[name]
            print(f"  {name}: {count} (+{delta})")

        # Category breakdown for knowledge_articles
        print("\n--- Knowledge Articles by Category ---")
        rows = db.execute(
            text("SELECT category, COUNT(*) FROM knowledge_articles GROUP BY category ORDER BY COUNT(*) DESC")
        ).fetchall()
        for row in rows:
            print(f"  {row[0]}: {row[1]}")

        # Salary benchmarks by experience level
        print("\n--- Salary Benchmarks by Experience Level ---")
        rows = db.execute(
            text("SELECT experience_level, COUNT(*) FROM salary_benchmarks GROUP BY experience_level ORDER BY experience_level")
        ).fetchall()
        for row in rows:
            print(f"  {row[0]}: {row[1]}")

        print("\n" + "=" * 60)
        print("Import complete!")
        print(f"  civil_service articles added: {cs_new}")
        print(f"  salary benchmarks added: {sb_new}")
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
