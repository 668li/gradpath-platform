"""就业率数字落库与报告状态推进（2026-09-29，DF-03b/c）。

输入：scripts/data/employment_rates_parsed.json（代理解析、已抽验）
动作（诚实分层）：
  1. 有数字的校 → employment_data 落行（report_id 关联, major='全校', degree=all）
     + report_records.parse_status → published（数字来自官方报告、带源可核）
  2. 无数字的校 → parse_status 保持 pending（如实挂账，展示层不计入）
  3. schools.employment_rate 只填 NULL 校且届别 ≥2023 且有数字——
     存量 122 校不覆盖，旧届别（2022 及以前）不填 school 字段（口径混用风险）

用法：python scripts/import_employment_rates.py [--dry-run]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.employment_data import Degree, EmploymentData
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School

DATA_FILE = BACKEND_ROOT / "scripts" / "data" / "employment_rates_parsed.json"
SCHOOL_RATE_MIN_YEAR = 2023  # school 字段只认较新届别


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if 0 < f <= 100 else None


def _int(v) -> int | None:
    if v is None:
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def main() -> None:
    dry = "--dry-run" in sys.argv
    items = json.loads(DATA_FILE.read_text(encoding="utf-8")).get("items", [])
    stats = {"ed_inserted": 0, "ed_skipped": 0, "published": 0, "kept_pending": 0,
             "school_rate_filled": 0, "no_report_row": 0}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as db:
        for it in items:
            uni = str(it.get("university_name") or "").strip()
            year_raw = it.get("report_year")
            if not uni or not str(year_raw or "").isdigit():
                continue
            year = int(year_raw)
            school = db.query(School).filter(School.name == uni).first()
            if school is None:
                continue
            report = (
                db.query(ReportRecord)
                .filter(ReportRecord.school_id == school.id, ReportRecord.year == year)
                .first()
            )
            if report is None:
                stats["no_report_row"] += 1
                continue
            er = _num(it.get("employment_rate"))
            fr = _num(it.get("further_study_rate"))
            tg = _int(it.get("total_graduates"))
            if er is None and fr is None:
                stats["kept_pending"] += 1
                continue
            if not dry:
                exists = (
                    db.query(EmploymentData)
                    .filter(
                        EmploymentData.report_id == report.id,
                        EmploymentData.major == "全校",
                        EmploymentData.degree == Degree.all,
                    )
                    .first()
                )
                if exists is None:
                    db.add(
                        EmploymentData(
                            report_id=report.id,
                            major="全校",
                            degree=Degree.all,
                            total_graduates=tg,
                            employment_rate=er,
                            further_study_rate=fr,
                        )
                    )
                    stats["ed_inserted"] += 1
                else:
                    stats["ed_skipped"] += 1
                report.parse_status = ParseStatus.published
                report.parsed_at = now
                stats["published"] += 1
                # school 字段：只填 NULL + 较新届别
                if school.employment_rate is None and er is not None and year >= SCHOOL_RATE_MIN_YEAR:
                    school.employment_rate = er
                    stats["school_rate_filled"] += 1
        if not dry:
            db.commit()
    print("done:", stats)


if __name__ == "__main__":
    main()
