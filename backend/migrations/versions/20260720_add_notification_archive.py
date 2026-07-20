"""为 notifications 表添加 archived / archived_at 字段（C4 通知归档）

Revision ID: add_notification_archive
Revises: add_pgtrgm_gin_indexes_v2
Create Date: 2026-07-20

C4 通知分区/归档：
- archived: 是否已归档（默认 false，索引加速过滤）
- archived_at: 归档时间（归档时设置，恢复时清空）

归档后的通知：
1. 不出现在主列表（默认 ?archived=false）
2. 不参与 unread_count 未读计数
3. 不受 mark_all_as_read 影响
4. 可在归档区查看与恢复
5. 由 delete_old_archived 定时任务物理清理（默认 90 天）
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_notification_archive"
down_revision: Union[str, None] = "add_pgtrgm_gin_indexes_v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # archived 字段：Boolean NOT NULL DEFAULT FALSE，加索引加速主列表过滤
    op.add_column(
        "notifications",
        sa.Column(
            "archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="是否已归档（归档通知从主列表移除）",
        ),
    )
    op.create_index(
        "ix_notifications_archived",
        "notifications",
        ["archived"],
    )

    # archived_at 字段：归档时间戳，nullable
    op.add_column(
        "notifications",
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="归档时间，归档时设置，恢复时清空",
        ),
    )


def downgrade() -> None:
    op.drop_column("notifications", "archived_at")
    op.drop_index("ix_notifications_archived", table_name="notifications")
    op.drop_column("notifications", "archived")
