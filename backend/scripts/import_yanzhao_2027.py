"""2027 研招目录行入库（2026-09-29，DF-05）。

输入：scripts/data/yanzhao_2027_batch.json（35 校核录：6 校 ok/29 校 not_published 如实）
动作：ok 校的 programs → grad_yanzhao_programs（year=2027，2026 旧值不删=bi-temporal）。
幂等：(university, major, degree, year) 先查后插；无源不入库。

用法：python scripts/import_yanzhao_2027.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.grad_intel import GradYanzhaoProgram

DATA_FILE = BACKEND_ROOT / "scripts" / "data" / "yanzhao_2027_batch.json"
URL_RE = re.compile(r"^https?://")


def _int(v) -> int | None:
    if v is None:
        return None
    s = str(v).strip()
    return int(s) if s.isdigit() and int(s) > 0 else None


def main() -> None:
    dry = "--dry-run" in sys.argv
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    inserted = skipped = not_published = 0
    seen: set[tuple[str, str, int]] = set()
    with SessionLocal() as db:
        for s in payload.get("schools", []):
            if s.get("status") != "ok":
                not_published += 1
                continue
            uni = str(s.get("university_name") or "").strip()
            url = str(s.get("source_url") or "").strip()
            year = int(s.get("year") or 2027)
            if not uni or not URL_RE.match(url):
                continue
            for p in s.get("programs", []):
                major = str(p.get("major_name") or "").strip()
                if not major:
                    continue
                if (uni, major, year) in seen:
                    skipped += 1
                    continue
                seen.add((uni, major, year))
                degree = str(p.get("degree_type") or "").strip() or None
                # 唯一索引 ix_yanzhao_unique = (university_name, major_name, year)，
                # 不含 degree_type：推免/统考目录同专业重复行会撞索引，幂等键必须对齐
                exists = (
                    db.query(GradYanzhaoProgram)
                    .filter(
                        GradYanzhaoProgram.university_name == uni,
                        GradYanzhaoProgram.major_name == major,
                        GradYanzhaoProgram.year == year,
                    )
                    .first()
                )
                if exists:
                    skipped += 1
                    continue
                db.add(
                    GradYanzhaoProgram(
                        university_name=uni,
                        department=str(p.get("department") or "").strip() or None,
                        major_name=major,
                        degree_type=degree,
                        enrollment_quota=_int(p.get("enrollment_quota")),
                        source_url=url,
                        year=year,
                        data_sources=[url],
                    )
                )
                inserted += 1
        if not dry:
            db.commit()
    print(f"done: inserted={inserted} skipped={skipped} not_published={not_published}")


if __name__ == "__main__":
    main()
