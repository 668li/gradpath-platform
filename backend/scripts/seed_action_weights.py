"""种子脚本入口：行动类型权重配置（t_action_weight）。

幂等执行：按 action_type 存在则跳过、缺失则插入（复用 app/seed/seed_action_weight.py）。
用法：python scripts/seed_action_weights.py
"""

import sys
from pathlib import Path

# 添加 backend 到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal  # noqa: E402
from app.seed.seed_action_weight import seed_action_weight  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        inserted = seed_action_weight(db)
        print(f"seed_action_weights: 新插入 {inserted} 条")
        from app.models.action_center import ActionWeight

        rows = db.query(ActionWeight).order_by(ActionWeight.weight).all()
        for r in rows:
            print(f"  {r.action_type:<16} weight={r.weight:<5} label={r.weight_label}")


if __name__ == "__main__":
    main()
