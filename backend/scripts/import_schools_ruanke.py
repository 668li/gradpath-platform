"""软科主榜院校入库（2026-08-16）：ruanke_rankings.json → schools 表 upsert。

策略（诚实优先 + 不覆盖既有真实数据）：
  - name 幂等：已存在的学校只补软科权威字段（province/level/ranking），
    不覆盖原有 report_index_url（考研人数据更有价值）；report_index_url 为空时填软科院校页
  - 新学校插入，slug 沿用 sch-sha256 规则；code 留空（软科无院校代码，不伪造）
  - key_majors 扩展存 {"tags", "category", "src"}：tags=软科标签、category=学科门类、src=榜单来源页
  - level 判定与既有逻辑一致：985 > 211 > 双一流 > None

来源：软科中国最好大学排名 2026 主榜（公开 JSON API，实测 200）。
全 ORM 参数绑定，幂等可重跑。
"""
import hashlib
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.school import School

DATA_FILE = Path(__file__).resolve().parent.parent / "app" / "crawlers" / "real_data" / "ruanke_rankings.json"
SOURCE_PAGE = "https://www.shanghairanking.cn/rankings/bcur/2026"


def _level_from_tags(tags: list) -> str | None:
    s = " ".join(str(t) for t in tags or [])
    if "985" in s:
        return "985"
    if "211" in s:
        return "211"
    if "双一流" in s:
        return "双一流"
    return None


def main() -> None:
    rows = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    inserted = updated = skipped_bad = 0
    with SessionLocal() as db:
        for r in rows:
            name = str(r.get("univNameCn") or "").strip()
            if not name or len(name) > 100:
                skipped_bad += 1
                continue
            tags = [str(t) for t in (r.get("univTags") or []) if str(t)]
            province = str(r.get("province") or "").strip()[:20] or None
            level = _level_from_tags(tags)
            ranking = int(r.get("ranking")) if str(r.get("ranking") or "").isdigit() else None
            slug = "sch-" + hashlib.sha256(name.encode()).hexdigest()[:10]
            univ_up = str(r.get("univUp") or "").strip()
            ruanke_page = f"https://www.shanghairanking.cn/institution/{univ_up}" if univ_up else None
            existing = db.query(School).filter(School.name == name).first()
            if existing:
                # 只补权威字段，不覆盖既有 report_index_url/key_majors 真实数据
                if province:
                    existing.province = province
                if level:
                    existing.level = level
                if ranking is not None:
                    existing.ranking = ranking
                if not existing.report_index_url and ruanke_page:
                    existing.report_index_url = ruanke_page
                updated += 1
                continue
            category = str(r.get("univCategory") or "").strip() or None
            db.add(
                School(
                    name=name,
                    slug=slug,
                    code=None,
                    province=province,
                    level=level,
                    ranking=ranking,
                    report_index_url=ruanke_page,
                    key_majors={"tags": tags, "category": category, "src": SOURCE_PAGE}
                    if (tags or category)
                    else None,
                )
            )
            inserted += 1
        db.commit()
        total = db.query(School).count()
    print(f"软科入库：新增 {inserted} / 更新 {updated} / 跳过 {skipped_bad} | schools 总数: {total}")


if __name__ == "__main__":
    main()
