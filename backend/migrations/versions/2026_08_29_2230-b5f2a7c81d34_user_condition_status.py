"""user_condition_status — 报考条件账本勾选状态

Revision ID: b5f2a7c81d34
Revises: c2d9e4f7a810
Create Date: 2026-08-29 22:30:00.000000+00:00

技能树 → 报考条件账本：用户对目标职位的每条报考条件维护
unmet/in_progress/met 三态进度。条件清单由 gwy_position 行规则
生成，本表只存勾选进度。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

import app.models.base

# revision identifiers, used by Alembic.
revision: str = 'b5f2a7c81d34'
down_revision: str | None = 'c2d9e4f7a810'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'user_condition_status',
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('user_id', app.models.base.GUID(), nullable=False),
        sa.Column('position_id', sa.String(length=32), nullable=False),
        sa.Column('condition_key', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='unmet'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'position_id', 'condition_key', name='uq_user_condition_key'),
    )
    op.create_index('ix_user_condition_status_user_id', 'user_condition_status', ['user_id'])
    op.create_index('ix_user_condition_status_position_id', 'user_condition_status', ['position_id'])


def downgrade() -> None:
    op.drop_index('ix_user_condition_status_position_id', table_name='user_condition_status')
    op.drop_index('ix_user_condition_status_user_id', table_name='user_condition_status')
    op.drop_table('user_condition_status')
