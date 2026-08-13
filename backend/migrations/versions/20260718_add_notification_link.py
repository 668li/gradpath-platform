"""为 notifications 表添加 link 列

Revision ID: add_notification_link
Revises: add_post_community_indexes
Create Date: 2026-07-18

- 支持通知点击跳转到相关页面（帖子/评论等）

从零升级：notifications 由 9c43ddf069ce 快照创建（快照已含 link 列），
故仅当目标表已存在（历史增量库补列场景）才执行。
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "add_notification_link"
down_revision: Union[str, None] = "add_post_community_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if _has_table("notifications"):
        op.add_column(
            "notifications",
            sa.Column("link", sa.String(length=500), nullable=True, comment="点击通知后跳转的链接"),
        )


def downgrade() -> None:
    if _has_table("notifications"):
        cols = {c["name"] for c in inspect(op.get_bind()).get_columns("notifications")}
        if "link" in cols:
            op.drop_column("notifications", "link")
