"""从本地导出受 users 外键影响丢数据的表 → 单个 jsonl 恢复包。

背景：2026-08-27 迁移后生产 users 表是新建的（UUID 带连字符），与本地
32 位无连字符 user_id 不一致，导致引用 users 的表在迁移时整表被外键拒绝：
experience_posts/qas/qa_answers/posts/grad_school_intel/civil_service_post_intel 等。
恢复流程：本地跑本脚本 → scp restore_bundle.jsonl → 容器内
python scripts/restore_user_fk_data.py /tmp/restore_bundle.jsonl

用法（本地）:
    py -3.13 scripts/export_restore_bundle.py
输出: 与脚本同目录 restore_bundle.jsonl
"""

import json
from datetime import date, datetime
from pathlib import Path

from app.database import Base, SessionLocal
from app.models import (
    DarkKnowledge,
    ExperiencePost,
    GradSchoolIntel,
    LearningResource,
    PathComparison,
    Post,
    PostIntel,
    QA,
    QAAnswer,
    QualityFeedback,
    SelfPositioning,
    StreakRecord,
    StudyPlan,
    UserOnboarding,
    UserSetting,
)

OUT_PATH = Path(__file__).resolve().parent / "restore_bundle.jsonl"

# 顺序即导入顺序：被依赖的表在前；posts 导出后按父先子后排序
MODELS = [
    GradSchoolIntel,
    PostIntel,
    LearningResource,
    ExperiencePost,
    DarkKnowledge,
    Post,
    QA,
    QAAnswer,
    PathComparison,
    SelfPositioning,
    StudyPlan,
    UserSetting,
    QualityFeedback,
    UserOnboarding,
    StreakRecord,
]


def serialize(value):
    from decimal import Decimal
    from uuid import UUID

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def main() -> None:
    db = SessionLocal()
    total = 0
    lines: list[str] = []
    for model in MODELS:
        rows = db.query(model).all()
        if model is Post:
            # 父帖在前，保证恢复时 parent_id 外键可满足
            rows.sort(key=lambda r: (r.parent_id is not None, r.id))
        count = 0
        for r in rows:
            rec = {
                c.name: serialize(getattr(r, c.name))
                for c in model.__table__.columns
                if getattr(r, c.name) is not None
            }
            lines.append(json.dumps({"table": model.__tablename__, "record": rec}, ensure_ascii=False))
            count += 1
        print(f"{model.__tablename__}: {count}")
        total += count
    db.close()
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"共 {total} 条 → {OUT_PATH}")


if __name__ == "__main__":
    main()
