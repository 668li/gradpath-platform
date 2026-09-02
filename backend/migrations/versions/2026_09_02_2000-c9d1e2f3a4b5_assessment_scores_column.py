"""assessment scores column (B2)

Revision ID: c9d1e2f3a4b5
Revises: c7d8e9f0a1b2
Create Date: 2026-09-02 20:00:00.000000+00:00

职业测评护城河改造（Phase B2）：assessments 新增 scores JSONB 列，持久化
每个测评的真实维度分（大五为各维度均分 dict[str,float]，其余为维度计数），
修正旧实现用 Counter(answers.values()) 把大五 Likert 选项计数当维度分的错误。

可空：旧行 scores=NULL，读取时由答案实时回填（见 api/assessment.py 的
_compute_scores_fallback），不回填也能渲染正确分数。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'c9d1e2f3a4b5'
# 挂到 c7d8e9f0a1b2（topic-gate），确保生产 `upgrade head` 单头线性链
# f4a7b8c9d1e2 → c7d8e9f0a1b2 → c9d1e2f3a4b5。误接 a1b2c3d4e5f6(08-13 老分支点)
# 会造成 side-branch，生产 upgrade head 不会自动应用本列 → scores 静默缺失。
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('scores', JSONB(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.drop_column('scores')
