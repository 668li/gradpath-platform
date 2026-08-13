"""添加导师评价系统表

Revision ID: add_mentor_tables
Revises:
Create Date: 2026-03-18

注意：本迁移的建表职责已由 9c43ddf069ce（autogenerate 完整快照）统一承担，
其 mentors / mentor_reviews 定义与当前模型同构（id=GUID、JSONB、server_default 齐备），
从零升级时空库由快照建表即可；历史增量库该 revision 早已 stamp 不会重跑。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "add_mentor_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 不再重复建表：mentors/mentor_reviews 由 9c43ddf069ce 快照统一创建，
    # 避免旧结构（String(32)/JSON/无 server_default）覆盖快照的新结构。
    return


def downgrade() -> None:
    # 与 upgrade 对称：从零库 downgrade 时这两张表已先被 9c43ddf069ce 的
    # downgrade 删除，这里仅当表仍存在才删除，避免「表不存在」报错。
    existing = set(inspect(op.get_bind()).get_table_names())
    if "mentor_reviews" in existing:
        op.drop_table("mentor_reviews")
    if "mentors" in existing:
        op.drop_table("mentors")
