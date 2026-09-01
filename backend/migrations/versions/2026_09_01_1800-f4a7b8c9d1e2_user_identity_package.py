"""users 加报考身份包列 — 预览/决策引擎身份持久化

Revision ID: f4a7b8c9d1e2
Revises: d3e5f7a9b2c4
Create Date: 2026-09-01 18:00:00.000000+00:00

把免费预览/决策引擎填过的报考身份（应届、政治面貌、学历、性别、基层经历）
持久化到 users 表：注册时可选带回，登录后自动预填，消除重复填表。
字段全 nullable（存量行不受影响），取值口径与 ConditionPreviewRequest/决策引擎一致。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f4a7b8c9d1e2'
down_revision: str | None = 'd3e5f7a9b2c4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('fresh_status', sa.String(length=10), nullable=True))
    op.add_column('users', sa.Column('party_status', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('education', sa.String(length=10), nullable=True))
    op.add_column('users', sa.Column('gender', sa.String(length=4), nullable=True))
    op.add_column('users', sa.Column('has_grassroots', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'has_grassroots')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'education')
    op.drop_column('users', 'party_status')
    op.drop_column('users', 'fresh_status')
