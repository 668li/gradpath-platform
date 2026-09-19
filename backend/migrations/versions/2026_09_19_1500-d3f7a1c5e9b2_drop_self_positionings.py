"""009 T1：self_positionings 表 drop（考研线收敛拍板①收尾）。

自我定位功能已随拍板①全链删除（页面/API/service/schema），表壳按"用户已批
drop 方向"移除。生产存量 4 行无保留价值，drop 前已按惯例双份备份
（容器 /tmp + 宿主机 ~/）。downgrade 忠实重建表壳（空表，无数据恢复）。

Revision ID: d3f7a1c5e9b2
Revises: b8e4f2a6c9d3
Create Date: 2026-09-19 15:00:00.000000+00:00

Revision 链：… → f1a3b5c7d9e2 → b8e4f2a6c9d3 → d3f7a1c5e9b2（单头线性）。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import JSONB, GUID

# revision identifiers, used by Alembic.
revision: str = "d3f7a1c5e9b2"
down_revision: Union[str, None] = "b8e4f2a6c9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("self_positionings")


def downgrade() -> None:
    op.create_table(
        "self_positionings",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("undergrad_tier", sa.String(length=50), nullable=False),
        sa.Column("undergrad_major", sa.String(length=200), nullable=True),
        sa.Column("gpa", sa.Float(), nullable=True),
        sa.Column("gpa_rank", sa.String(length=50), nullable=True),
        sa.Column("english_level", sa.String(length=50), nullable=True),
        sa.Column("english_score", sa.Integer(), nullable=True),
        sa.Column("research_experience", sa.Text(), nullable=True),
        sa.Column("competitions", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("awards", sa.Text(), nullable=True),
        sa.Column("internships", sa.Text(), nullable=True),
        sa.Column("target_school", sa.String(length=200), nullable=True),
        sa.Column("target_major", sa.String(length=200), nullable=True),
        sa.Column("target_region", sa.String(length=100), nullable=True),
        sa.Column("other_info", sa.Text(), nullable=True),
        sa.Column("ai_assessment", sa.Text(), nullable=True),
        sa.Column("reach_schools", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("target_schools", JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("safety_schools", JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("success_probability", sa.Integer(), nullable=True),
        sa.Column("risk_warnings", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_self_positionings_user_id", "self_positionings", ["user_id"])
