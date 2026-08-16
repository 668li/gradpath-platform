"""真实导师数据入库（2026-08-16）：mentor_edu_data.json → mentors 表。

数据源（agent 采集，3 校试点）：浙江大学基础医学系博导名录 / 华中科技大学
教师主页系统 / 深圳大学数学学院师资页，共 45 条，全部 .edu.cn 官网公开简介。

映射原则（诚实优先）：
  - name/university/department/title/research_directions 直接映射
  - academic_homepage ← homepage_url；google_scholar_url/cnki_url 留空（未采集）
  - paper_count/project_count/citation_count 保持 0（默认值，官网简介无此数据，不伪造）
  - enrollment_status 保持 "unknown"（源页未标注招生状态）
  - contact_email/contact_phone 一律 None（红线：联系方式不入库）
  - 溯源：无独立列，research_directions 尾部追加 "src:{source_url}"（可检索）

幂等：(name, university) 去重跳过。全 ORM 参数绑定。
"""
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.mentor import Mentor

DATA_FILE = BACKEND_ROOT / "app" / "crawlers" / "real_data" / "mentor_edu_data.json"


def main() -> None:
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DATA_FILE
    rows = json.loads(target.read_text(encoding="utf-8"))
    inserted = duplicated = 0
    with SessionLocal() as db:
        for r in rows:
            name = str(r.get("name") or "").strip()[:100]
            university = str(r.get("university") or "").strip()[:200]
            department = str(r.get("department") or "").strip()[:200]
            title = str(r.get("title") or "未知").strip()[:100]
            if not name or not university or not department:
                continue
            exists = (
                db.query(Mentor.id)
                .filter(Mentor.name == name, Mentor.university == university)
                .first()
            )
            if exists:
                duplicated += 1
                continue
            fields_raw = str(r.get("research_fields") or "").strip()
            directions = [f.strip() for f in fields_raw.replace("，", ",").replace("、", ",").split(",") if f.strip()]
            source_url = str(r.get("source_url") or "").strip()
            if source_url:
                directions = directions[:8] + [f"src:{source_url[:200]}"]
            db.add(
                Mentor(
                    name=name,
                    university=university,
                    department=department,
                    title=title,
                    research_directions=directions,
                    academic_homepage=str(r.get("homepage_url") or "").strip()[:500] or None,
                )
            )
            inserted += 1
        db.commit()
        total = db.query(Mentor).count()
    print(f"入库 {inserted} 位 / 重复 {duplicated} | mentors 总数: {total}")


if __name__ == "__main__":
    main()
