"""为 notifications 表添加 link 列

Revision ID: add_notification_link
Revises: add_pgtrgm_gin_indexes
Create Date: 2026-07-18

- 支持通知点击跳转到相关页面（帖子/评论等）
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_notification_link"
down_revision: Union[str, None] = "add_post_community_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("link", sa.String(length=500), nullable=True, comment="点击通知后跳转的链接"),
    )


def downgrade() -> None:
    op.drop_column("notifications", "link")
