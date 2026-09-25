"""复盘深化：原则库 + Try 行动卡（2026-09-25 用户拍板"聚焦模拟器+复盘两功能做深"）。

新建两表（对抗审查裁决后收敛版）：
- retro_principles：复盘原则库，唯一真相源（不做 user_memory_facts 双写，chat 注入直查本表）
- retro_actions：Try 行动卡（下次再发生怎么办），带复审日期，复盘开场先复审到期卡

刻意不改 MemoryFactType 枚举：原则只住 retro_principles，避免双真相源漂移。

downgrade 忠实回滚：两表 drop + 两个状态枚举 drop。

Revision 链：… → d3f7a1c5e9b2 → e9c2a7d4f1b3 → e9c2a7d4f1b4 → a7f3c8d2e1b9（单头线性）。

Revision ID: a7f3c8d2e1b9
Revises: e9c2a7d4f1b4
Create Date: 2026-09-25 20:00:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "a7f3c8d2e1b9"
down_revision: Union[str, None] = "e9c2a7d4f1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 枚举类型名与 app/models/retrospective.py 中 Enum(name=...) 严格一致；
# 成员值与成员名相同（本仓枚举约定），迁移内用字面量避免耦合活代码。
_E_PRINCIPLE_STATUS = sa.Enum("draft", "verified", "invalid", name="principlestatus")
_E_ACTION_STATUS = sa.Enum(
    "pending", "effective", "ineffective", "not_met", name="retroactionstatus"
)

_ALL_ENUMS = (_E_PRINCIPLE_STATUS, _E_ACTION_STATUS)


def upgrade() -> None:
    # 注意：枚举不在此处预创建——create_table 的内联 ENUM 会自动 CREATE TYPE，
    # 预创建+内联=自伤型 DuplicateObject（2026-09-25 生产首炸实测）。
    op.create_table(
        "retro_principles",
        sa.Column("id", GUID(), primary_key=True, autoincrement=False),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("trigger_scene", sa.String(200), nullable=False),
        sa.Column("action", sa.String(400), nullable=False),
        sa.Column("rationale", sa.String(500), nullable=True),
        sa.Column("scene_tags", JSONB(), nullable=False),
        sa.Column("status", _E_PRINCIPLE_STATUS, nullable=False, index=True),
        sa.Column("verify_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "source_retro_id",
            GUID(),
            sa.ForeignKey("retrospectives.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_snapshot", JSONB(), nullable=False),
        sa.Column("next_review_at", sa.Date(), nullable=True, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "retro_actions",
        sa.Column("id", GUID(), primary_key=True, autoincrement=False),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "retro_id",
            GUID(),
            sa.ForeignKey("retrospectives.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("content", sa.String(400), nullable=False),
        sa.Column("trigger_scene", sa.String(200), nullable=False),
        sa.Column("status", _E_ACTION_STATUS, nullable=False, index=True),
        sa.Column("review_due_at", sa.Date(), nullable=False, index=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(500), nullable=True),
        sa.Column(
            "principle_id",
            GUID(),
            sa.ForeignKey("retro_principles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("retro_actions")
    op.drop_table("retro_principles")
    # drop_table 不级联删枚举类型，须显式清（checkfirst 防 PG 依赖残留误炸）
    _E_ACTION_STATUS.drop(op.get_bind(), checkfirst=True)
    _E_PRINCIPLE_STATUS.drop(op.get_bind(), checkfirst=True)