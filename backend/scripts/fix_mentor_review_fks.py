"""一次性修复 mentor_reviews 无效外键存量数据（P4）。

背景：mentor_reviews.mentor_id / user_id 存在指向已删除记录的存量数据
（约 319 条），导致 JOIN 悬空、前端展示失效。

修复规则：
- mentor_id 不存在于 mentors → 删除整行（导师不存在，评价无意义）
- user_id 不存在于 users → 按列约束处理：
    列可空 → 置 NULL 保留评价内容；列 NOT NULL → 删除整行

安全：默认仅预览统计与样本，不落库；加 --execute 才实际修复。
用法（在 backend 目录下运行）：
    python scripts/fix_mentor_review_fks.py             # 预览
    python scripts/fix_mentor_review_fks.py --execute   # 实际修复
"""
import argparse
import logging
import sys
from pathlib import Path

# 以脚本形式运行时把 backend 加入 sys.path（与 seed_mentor_data.py 同款）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, text, update  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.models.mentor_review import MentorReview  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("fix_mentor_review_fks")

# 关联目标表名（GUID 主键均为 id 字符串）
_FK_TARGETS = {
    "mentor_id": "mentors",   # 无效 → 删行
    "user_id": "users",       # 无效 → 按列约束（NOT NULL 则删行）
}


def _column_nullable(db_engine: Engine, table: str, column: str) -> bool:
    """查询 SQLite/PostgreSQL 列是否可空。"""
    with db_engine.connect() as conn:
        if db_engine.dialect.name == "sqlite":
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            for cid, name, ctype, notnull, dflt, pk in rows:
                if name == column:
                    return not bool(notnull)
        else:
            rows = conn.execute(
                text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = :c"
                ),
                {"t": table, "c": column},
            ).fetchall()
            if rows:
                return rows[0][0].lower() == "yes"
    return True  # 未知方言/列不存在时保守按可空处理（只置 NULL，不删行）


def _invalid_rows(db, fk_column: str) -> list[dict]:
    """返回 mentor_reviews 中 fk_column 无效的行（id / fk / title）。"""
    sql = text(
        f"""
        SELECT r.id, r.{fk_column}, r.title
        FROM mentor_reviews r
        WHERE r.{fk_column} IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM {_FK_TARGETS[fk_column]} p WHERE p.id = r.{fk_column}
          )
        """
    )
    return [{"id": row[0], fk_column: row[1], "title": row[2]} for row in db.execute(sql).fetchall()]


def analyze_and_fix(execute: bool = False) -> None:
    """预览/修复 mentor_reviews 无效外键。

    Args:
        execute: False 只打印统计与样本；True 实际落库修复
    """
    total_invalid = 0
    with SessionLocal() as db:
        for fk_column, target in _FK_TARGETS.items():
            rows = _invalid_rows(db, fk_column)
            if not rows:
                logger.info("%s: 无无效行", fk_column)
                continue

            nullable = _column_nullable(engine, "mentor_reviews", fk_column)
            action = "置 NULL 保留" if nullable else "删除整行"
            total_invalid += len(rows)
            logger.info(
                "%s: %d 行无效（目标表 %s，列%s可空 → %s）",
                fk_column, len(rows), target, "" if nullable else "不", action,
            )
            for sample in rows[:5]:
                logger.info("  样本 id=%s title=%r", sample["id"], (sample["title"] or "")[:40])

            if not execute:
                continue

            if nullable:
                db.execute(
                    update(MentorReview)
                    .where(MentorReview.id.in_([r["id"] for r in rows]))
                    .values(**{fk_column: None})
                )
                logger.info("  已置 NULL %d 行", len(rows))
            else:
                db.execute(
                    delete(MentorReview).where(MentorReview.id.in_([r["id"] for r in rows]))
                )
                logger.info("  已删除 %d 行", len(rows))

        if execute:
            db.commit()
            logger.info("已提交修复")
        else:
            logger.info("预览模式（未落库），共 %d 行无效外键；加 --execute 实际修复", total_invalid)


def main() -> None:
    parser = argparse.ArgumentParser(description="修复 mentor_reviews 无效外键（默认预览）")
    parser.add_argument("--execute", action="store_true", help="实际落库修复（默认仅预览）")
    args = parser.parse_args()
    analyze_and_fix(execute=args.execute)


if __name__ == "__main__":
    main()
