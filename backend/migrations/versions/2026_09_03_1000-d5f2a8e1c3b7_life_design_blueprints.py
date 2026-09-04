"""life design blueprints table (认识自己 V1)

Revision ID: d5f2a8e1c3b7
Revises: c9d1e2f3a4b5
Create Date: 2026-09-03 10:00:00.000000+00:00

「认识自己」重设计 V1：新增 life_design_blueprints 表，持久化斯坦福人生设计
访谈（life_design skill，⟨DONE⟩ 轮）产出的《个人人生设计蓝图》。
同一用户可多版本（再访谈），transcript 保存问答记录供复盘。

Revision 链：... → c7d8e9f0a1b2 → c9d1e2f3a4b5 → d5f2a8e1c3b7（单头线性）。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID, JSONB

# revision identifiers, used by Alembic.
revision: str = 'd5f2a8e1c3b7'
down_revision: Union[str, None] = 'c9d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'life_design_blueprints',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('conversation_id', GUID(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('transcript', JSONB(), nullable=False, server_default='[]'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='completed'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_life_design_blueprints_user_id', 'life_design_blueprints', ['user_id']
    )


def downgrade() -> None:
    op.drop_index('ix_life_design_blueprints_user_id', table_name='life_design_blueprints')
    op.drop_table('life_design_blueprints')
