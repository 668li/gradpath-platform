"""quality reasons and feedback (Phase I)

Revision ID: 734e443c3f82
Revises: 31bf30021f5a
Create Date: 2026-08-15 14:21:02.990137+00:00

证据链 + 反馈闭环（Phase I）：experience_posts / kaoyan_news 新增
quality_reasons（质量分扣分原因，前端徽章可解释），新建 quality_feedback
表（用户对质量分/证据链的双键反馈，同用户同条目幂等 upsert）。
注意：autogenerate 带入的历史漂移已手动裁剪，仅保留本表变更。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID, JSONB

# revision identifiers, used by Alembic.
revision: str = '734e443c3f82'
down_revision: Union[str, None] = '31bf30021f5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'quality_feedback',
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('target_type', sa.Enum('experience_post', 'kaoyan_news', name='qualityfeedbacktargettype'), nullable=False),
        sa.Column('target_id', sa.String(length=64), nullable=False),
        sa.Column('feedback_type', sa.Enum('helpful', 'unhelpful', name='qualityfeedbacktype'), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=True),
        sa.Column('id', GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'target_type', 'target_id', name='uq_quality_feedback_user_target'),
    )
    with op.batch_alter_table('quality_feedback', schema=None) as batch_op:
        batch_op.create_index('ix_quality_feedback_target', ['target_type', 'target_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_quality_feedback_user_id'), ['user_id'], unique=False)

    with op.batch_alter_table('experience_posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quality_reasons', JSONB(), nullable=True))

    with op.batch_alter_table('kaoyan_news', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quality_reasons', JSONB(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('kaoyan_news', schema=None) as batch_op:
        batch_op.drop_column('quality_reasons')

    with op.batch_alter_table('experience_posts', schema=None) as batch_op:
        batch_op.drop_column('quality_reasons')

    with op.batch_alter_table('quality_feedback', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_quality_feedback_user_id'))
        batch_op.drop_index('ix_quality_feedback_target')

    op.drop_table('quality_feedback')
