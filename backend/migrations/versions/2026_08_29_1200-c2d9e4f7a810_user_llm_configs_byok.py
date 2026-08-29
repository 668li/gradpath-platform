"""user_llm_configs — BYOK 用户自带 LLM API 配置

Revision ID: c2d9e4f7a810
Revises: a91f0c8d2e63
Create Date: 2026-08-29 12:00:00.000000+00:00

AgentChat BYOK：服务器未配置 LLM_API_KEY 时，用户可填自己的
OpenAI 兼容 API Key 启用 AI 对话。api_key 经 Fernet 加密落库。
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

import app.models.base

# revision identifiers, used by Alembic.
revision: str = 'c2d9e4f7a810'
down_revision: str | None = 'a91f0c8d2e63'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'user_llm_configs',
        sa.Column('id', app.models.base.GUID(), nullable=False),
        sa.Column('user_id', app.models.base.GUID(), nullable=False),
        sa.Column('provider', sa.String(length=30), nullable=False, server_default='custom'),
        sa.Column('base_url', sa.String(length=500), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_user_llm_configs_user_id'),
    )
    op.create_index('ix_user_llm_configs_user_id', 'user_llm_configs', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_user_llm_configs_user_id', table_name='user_llm_configs')
    op.drop_table('user_llm_configs')
