"""experience post purity and kaoyan news structured meta (Phase G)

Revision ID: 31bf30021f5a
Revises: 8d1a91d30ed3
Create Date: 2026-08-15 11:22:54.066369+00:00

考研信息差升级（经验闭环核心）：experience_posts 新增提纯与质量列
（质量分/反软广/结构化元信息），kaoyan_news 新增 structured_meta 决策数据卡。
注意：autogenerate 带入的历史漂移已手动裁剪，仅保留本表变更。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import JSONB

# revision identifiers, used by Alembic.
revision: str = '31bf30021f5a'
down_revision: Union[str, None] = '8d1a91d30ed3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 注意：三个本应 NOT NULL 的列（structured_meta/is_promotion/promotion_confidence）
    # 在 SQLite 上对已有数据的表加 NOT NULL 列必须带 server_default，而 server_default
    # 会与模型的 Python 端 default 形成 alembic check 漂移。故按仓库惯例改为可空，
    # 模型端 default 保证新插入行始终有值；NULL 语义=旧数据未检测（前端按 False/{} 兜底）。
    with op.batch_alter_table('experience_posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quality_score', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('quality_grade', sa.String(length=2), nullable=True))
        batch_op.add_column(sa.Column('ai_summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('structured_meta', JSONB(), nullable=True))
        batch_op.add_column(sa.Column('is_promotion', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('promotion_confidence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('promotion_reason', sa.String(length=200), nullable=True))

    with op.batch_alter_table('kaoyan_news', schema=None) as batch_op:
        batch_op.add_column(sa.Column('structured_meta', JSONB(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('kaoyan_news', schema=None) as batch_op:
        batch_op.drop_column('structured_meta')

    with op.batch_alter_table('experience_posts', schema=None) as batch_op:
        batch_op.drop_column('promotion_reason')
        batch_op.drop_column('promotion_confidence')
        batch_op.drop_column('is_promotion')
        batch_op.drop_column('structured_meta')
        batch_op.drop_column('ai_summary')
        batch_op.drop_column('quality_grade')
        batch_op.drop_column('quality_score')
