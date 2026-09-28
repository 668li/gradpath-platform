"""自划线院校复试分数线入库（2026-09-29，DF-01）：scoreline_batch_*.json → grad_scoreline_records。

策略（官网标定路线，任务书 docs/数据填充任务书-2026-09-27.md DF-01）：
  - 只收 status=ok 且 source_url 为 http(s) 的校年（无源不入库红线）
  - total_score_line 非正整数或缺失的行跳过（引擎将 0 视为脏占位）
  - 幂等：university_name+major_name+degree_type+year 已存在则跳过（先查后插）
  - data_sources = [官网公示页 URL]，过引擎溯源闸（含 http 即可）
  - 40 校上限、目标 ≥25 校由数据文件决定，脚本不追全量

用法：python scripts/import_scoreline_official.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.grad_intel import GradScorelineRecord

DATA_DIR = BACKEND_ROOT / "scripts" / "data"
URL_RE = re.compile(r"^https?://")


def _clean_int(v) -> int | None:
    """表格转录来的整数清洗：非正整数（含 0/None/垃圾串）→ None。"""
    if v is None:
        return None
    s = str(v).strip()
    if not s.isdigit():
        return None
    n = int(s)
    return n if n > 0 else None


def parse_batches(paths: list[Path]) -> tuple[list[GradScorelineRecord], dict]:
    """纯函数：batch JSON → 待插 ORM 行 + 统计。不碰 DB，便于测试锁定。"""
    records: list[GradScorelineRecord] = []
    stats = {
        "school_years_ok": 0,
        "school_years_not_found": 0,
        "rows_kept": 0,
        "rows_dropped_no_url": 0,
        "rows_dropped_bad_total": 0,
    }
    seen_keys: set[tuple[str, str, str | None, int]] = set()
    for path in paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for block in payload.get("schools", []):
            uni = str(block.get("university_name") or "").strip()
            year_raw = block.get("year")
            if block.get("status") != "ok":
                stats["school_years_not_found"] += 1
                continue
            url = str(block.get("source_url") or "").strip()
            if not uni or not str(year_raw or "").isdigit() or not URL_RE.match(url):
                stats["school_years_not_found"] += 1
                continue
            year = int(year_raw)
            stats["school_years_ok"] += 1
            for ln in block.get("lines", []):
                major = str(ln.get("major_name") or "").strip()
                if not major:
                    continue
                total = _clean_int(ln.get("total_score_line"))
                if total is None:
                    stats["rows_dropped_bad_total"] += 1
                    continue
                if not URL_RE.match(url):
                    stats["rows_dropped_no_url"] += 1
                    continue
                degree = str(ln.get("degree_type") or "").strip() or None
                key = (uni, major, degree, year)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                records.append(
                    GradScorelineRecord(
                        university_name=uni,
                        major_name=major,
                        degree_type=degree,
                        year=year,
                        total_score_line=total,
                        politics_score=_clean_int(ln.get("politics_score")),
                        foreign_language_score=_clean_int(ln.get("foreign_language_score")),
                        business_1_score=_clean_int(ln.get("business_1_score")),
                        business_2_score=_clean_int(ln.get("business_2_score")),
                        data_sources=[url],
                    )
                )
                stats["rows_kept"] += 1
    return records, stats


def main() -> None:
    dry = "--dry-run" in sys.argv
    paths = sorted(DATA_DIR.glob("scoreline_batch_*.json"))
    if not paths:
        print("no batch files found under", DATA_DIR)
        return
    records, stats = parse_batches(paths)
    unis = {r.university_name for r in records}
    print(
        f"parsed: school-years ok={stats['school_years_ok']} "
        f"not_found={stats['school_years_not_found']} rows_kept={stats['rows_kept']} "
        f"dropped(bad_total={stats['rows_dropped_bad_total']}, no_url={stats['rows_dropped_no_url']}) "
        f"universities={len(unis)}"
    )
    if dry:
        for u in sorted(unis):
            n = sum(1 for r in records if r.university_name == u)
            print(f"  {u}: {n} rows")
        return
    inserted = skipped = 0
    with SessionLocal() as db:
        for r in records:
            q = (
                db.query(GradScorelineRecord)
                .filter(
                    GradScorelineRecord.university_name == r.university_name,
                    GradScorelineRecord.major_name == r.major_name,
                    GradScorelineRecord.degree_type == r.degree_type,
                    GradScorelineRecord.year == r.year,
                )
                .first()
            )
            if q:
                skipped += 1
                continue
            db.add(r)
            inserted += 1
        db.commit()
    print(f"db: inserted={inserted} skipped_existing={skipped}")


if __name__ == "__main__":
    main()
