# backend/app/seed/seed_action_weight.py
"""行动类型权重配置种子数据 — 对齐系统设计 §4.2.4（D18）。

7 条默认行动类型权重，幂等 upsert：按 action_type 存在则跳过、缺失则插入。
"""

from sqlalchemy.orm import Session

from app.models.action_center import ActionWeight

# (action_type, weight, weight_label)
ACTION_WEIGHTS = [
    ("read_article", 1, "阅读文章"),
    ("finish_course", 5, "完成课程"),
    ("resume_revise", 10, "简历修改"),
    ("mock_interview", 15, "模拟面试"),
    ("real_apply", 20, "实际投递"),
    ("get_offer", 100, "拿到Offer"),
    ("custom", 1, "自定义行动"),
]


def seed_action_weight(db: Session) -> int:
    """幂等插入行动类型权重（按 action_type 去重）。

    Returns:
        新插入的记录数量
    """
    inserted = 0
    for action_type, weight, weight_label in ACTION_WEIGHTS:
        existing = db.query(ActionWeight).filter(ActionWeight.action_type == action_type).first()
        if existing:
            continue
        db.add(
            ActionWeight(
                action_type=action_type,
                weight=weight,
                weight_label=weight_label,
            )
        )
        inserted += 1
    db.commit()
    return inserted


if __name__ == "__main__":
    from app.database import SessionLocal

    with SessionLocal() as db:
        count = seed_action_weight(db)
        print(f"seed_action_weight: 新插入 {count} 条")
        rows = db.query(ActionWeight).order_by(ActionWeight.weight).all()
        for r in rows:
            print(f"  {r.action_type:<16} weight={r.weight:<5} label={r.weight_label}")
