"""真实公司数据入库（2026-08-16）：company_public_data.json → companies 表。

数据源（agent 采集，robots 合规验证）：
  - 2025《财富》中国500强（500 家）
  - 中国互联网协会 2025 互联网企业综合实力前百家（100 家）
  - 深交所上市公司列表采样（60 家）
  跨源去重后 653 家，全部带 source_url。

映射：name 唯一去重；size 从员工数字符串解析（<50 startup / <200 small /
<2000 medium / <10000 large / ≥10000 giant），无员工数据的上市/百强企业
推断为 large 并在 description 注明「规模推断」；溯源 URL 追加在 description 尾行。
幂等：name 冲突跳过。全 ORM。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.company import Company, CompanySize

DATA = Path(__file__).resolve().parent.parent / "app" / "crawlers" / "real_data" / "company_public_data.json"


def _parse_size(size_str: str) -> CompanySize | None:
    m = re.search(r"(\d+)", str(size_str or ""))
    if not m:
        return None
    n = int(m.group(1))
    if n < 50:
        return CompanySize.startup
    if n < 200:
        return CompanySize.small
    if n < 2000:
        return CompanySize.medium
    if n < 10000:
        return CompanySize.large
    return CompanySize.giant


def main() -> None:
    rows = json.load(open(DATA, encoding="utf-8"))
    inserted = duplicated = 0
    with SessionLocal() as db:
        for r in rows:
            name = str(r.get("name") or "").strip()[:200]
            industry = str(r.get("industry") or "综合").strip()[:50]
            if not name:
                continue
            if db.query(Company.id).filter(Company.name == name).first():
                duplicated += 1
                continue
            size = _parse_size(r.get("size"))
            size_note = ""
            if size is None:
                size = CompanySize.large
                size_note = "（规模按上市/百强推断）"
            desc = str(r.get("description") or "").strip()
            source_url = str(r.get("source_url") or "").strip()
            if source_url:
                desc = f"{desc}\n来源：{source_url}"
            db.add(
                Company(
                    name=name,
                    industry=industry,
                    size=size,
                    stage=None,
                    headquarters=str(r.get("city") or "").strip()[:50] or None,
                    description=(desc + size_note) or None,
                )
            )
            inserted += 1
        db.commit()
    print(f"入库 {inserted} 家 / 重复跳过 {duplicated} / 源 {len(rows)} 条")


if __name__ == "__main__":
    main()
