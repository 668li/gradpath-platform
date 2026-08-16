"""删除历史合成种子数据（2026-08-16 用户拍板「换成真的，删除假的」）。

对象（全部为 seed/expand 系列脚本生成的合成数据，非真实爬取）：
  - mentors 318 + mentor_reviews 2（引用 mentors，一并删）
  - dark_knowledge 73 + dark_knowledge_push_log（引用，一并删）
  - salary_benchmarks 2880
  - knowledge_articles 30
  - companies 53（companies 无引用；company_reviews 已为 0）

安全措施：
  - 删除前全量导出 JSON 归档到 scripts/archive/synthetic_purge_2026-08-16/（可追溯，符合审计习惯）
  - 全程 ORM 参数绑定
  - 幂等：重跑时各表已空则跳过
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.company import Company
from app.models.grad_intel import DarkKnowledge
from app.models.knowledge_article import KnowledgeArticle
from app.models.mentor import Mentor
from app.models.mentor_review import MentorReview
from app.models.salary_benchmark import SalaryBenchmark
from app.models.dark_knowledge_push import DarkKnowledgePushLog

ARCHIVE = Path(__file__).resolve().parent / "archive" / "synthetic_purge_2026-08-16"


def _dump(db, model, name: str) -> int:
    rows = db.query(model).all()
    data = []
    for r in rows:
        item = {}
        for col in model.__table__.columns.keys():
            v = getattr(r, col)
            if v is not None and not isinstance(v, (int, float, bool, str)):
                v = str(v)
            item[col] = v
        data.append(item)
    if data:
        ARCHIVE.mkdir(parents=True, exist_ok=True)
        with open(ARCHIVE / f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    return len(data)


def main() -> None:
    with SessionLocal() as db:
        for model, name, label in [
            (MentorReview, "mentor_reviews", "导师评价(合成)"),
            (Mentor, "mentors", "导师(合成)"),
            (DarkKnowledgePushLog, "dark_knowledge_push_log", "暗知识推送日志"),
            (DarkKnowledge, "dark_knowledge", "暗知识(合成)"),
            (SalaryBenchmark, "salary_benchmarks", "薪资基准(合成)"),
            (KnowledgeArticle, "knowledge_articles", "知识文章(合成)"),
            (Company, "companies", "公司(合成)"),
        ]:
            n = _dump(db, model, name)
            deleted = db.query(model).delete()
            print(f"{label:22s} 备份 {n:>5} 条 → 已删除 {deleted:>5} 条")
        db.commit()
    print(f"归档目录: {ARCHIVE}")


if __name__ == "__main__":
    main()
