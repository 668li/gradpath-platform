"""就业质量报告记录入库（2026-09-29，DF-03）：employment_reports_batch.json → report_records。

策略（诚实分层）：
  - 只收 status=ok 且 source_url 为 http(s) 官方域名的校（无源不入库红线）
  - year=报告届别年份（report_year），非入库年份——页面展示口径即届别
  - 幂等：(school_id, year) 唯一约束冲突跳过（先查后插）
  - parse_status='pending'：本脚本只落报告索引，就业率数字由解析管道另行抽取后更新
  - schools.employment_rate 不动（存量 122 校已有值不覆盖；NULL 补值仅在解析出较新届别
    数字后由解析脚本处理，且只填 NULL）

用法：python scripts/import_employment_reports.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School
from app.models.pipeline_enums import SourceType

DATA_FILES = [
    BACKEND_ROOT / "scripts" / "data" / "employment_reports_batch.json",
    BACKEND_ROOT / "scripts" / "data" / "employment_reports_batch2.json",
]
URL_RE = re.compile(r"^https?://")
OFFICIAL_DOMAIN_RE = re.compile(r"^https?://[^/]*\.edu\.cn")


def parse_batch(payload: dict) -> tuple[list[dict], dict]:
    """纯函数：batch JSON → 合法入参列表 + 统计。不碰 DB。"""
    rows: list[dict] = []
    stats = {"ok": 0, "not_found": 0, "dropped_bad_url": 0, "dropped_not_official": 0}
    for s in payload.get("schools", []):
        if s.get("status") != "ok":
            stats["not_found"] += 1
            continue
        uni = str(s.get("university_name") or "").strip()
        year_raw = s.get("report_year")
        url = str(s.get("source_url") or "").strip()
        if not uni or not str(year_raw or "").isdigit():
            stats["not_found"] += 1
            continue
        if not URL_RE.match(url):
            stats["dropped_bad_url"] += 1
            continue
        if not OFFICIAL_DOMAIN_RE.match(url):
            stats["dropped_not_official"] += 1
            continue
        rows.append(
            {
                "university_name": uni,
                "year": int(year_raw),
                "source_url": url,
                "pdf_hint": str(s.get("pdf_hint") or "").strip() or None,
                "page_numbers": [str(x) for x in (s.get("page_numbers") or []) if str(x)],
            }
        )
        stats["ok"] += 1
    return rows, stats


def main() -> None:
    dry = "--dry-run" in sys.argv
    payloads: list[dict] = []
    for f in DATA_FILES:
        if f.exists():
            payloads.append(json.loads(f.read_text(encoding="utf-8")))
    if not payloads:
        print("no batch files under scripts/data/")
        return
    rows: list[dict] = []
    for p in payloads:
        r, s = parse_batch(p)
        rows.extend(r)
        print(f"parsed: ok={s['ok']} not_found={s['not_found']} "
              f"bad_url={s['dropped_bad_url']} not_official={s['dropped_not_official']}")
    if dry:
        for r in rows:
            print(f"  {r['university_name']} {r['year']} {r['source_url'][:70]}")
        return
    inserted = skipped = unmatched = 0
    with SessionLocal() as db:
        for r in rows:
            school = db.query(School).filter(School.name == r["university_name"]).first()
            if school is None:
                unmatched += 1
                continue
            exists = (
                db.query(ReportRecord)
                .filter(
                    ReportRecord.school_id == school.id,
                    ReportRecord.year == r["year"],
                )
                .first()
            )
            if exists:
                skipped += 1
                continue
            db.add(
                ReportRecord(
                    school_id=school.id,
                    year=r["year"],
                    source_url=r["source_url"],
                    source_type=SourceType.crawl,
                    parse_status=ParseStatus.pending,
                )
            )
            inserted += 1
        db.commit()
    print(f"db: inserted={inserted} skipped_existing={skipped} unmatched_school={unmatched}")


if __name__ == "__main__":
    main()
