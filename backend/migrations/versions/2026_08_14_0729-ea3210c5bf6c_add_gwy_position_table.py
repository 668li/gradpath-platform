"""add gwy_position table

Revision ID: ea3210c5bf6c
Revises: df1a2b3c4d5e
Create Date: 2026-08-14 07:29:33.530102+00:00

仅包含 gwy_position 建表。autogenerate 一并检测到的其它表历史漂移
（列/索引/类型与模型不一致，create_all+stamp 历史产物所致）不属于
本次变更范围，已从本迁移剔除，避免升级时误改既有表结构。

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ea3210c5bf6c'
down_revision: Union[str, None] = 'df1a2b3c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('gwy_position',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('exam_type', sa.String(length=20), nullable=False),
    sa.Column('dept_code', sa.String(length=50), nullable=True),
    sa.Column('dept_name', sa.String(length=200), nullable=True),
    sa.Column('bureau', sa.String(length=200), nullable=True),
    sa.Column('agency_type', sa.String(length=100), nullable=True),
    sa.Column('position_name', sa.String(length=200), nullable=True),
    sa.Column('position_attr', sa.String(length=100), nullable=True),
    sa.Column('position_distribution', sa.String(length=200), nullable=True),
    sa.Column('position_desc', sa.Text(), nullable=True),
    sa.Column('position_code', sa.String(length=50), nullable=False),
    sa.Column('org_level', sa.String(length=50), nullable=True),
    sa.Column('exam_category', sa.String(length=50), nullable=True),
    sa.Column('recruit_count', sa.Integer(), nullable=True),
    sa.Column('major_req', sa.Text(), nullable=True),
    sa.Column('education_req', sa.String(length=100), nullable=True),
    sa.Column('degree_req', sa.String(length=100), nullable=True),
    sa.Column('political_status', sa.String(length=50), nullable=True),
    sa.Column('min_work_years', sa.String(length=50), nullable=True),
    sa.Column('grassroots_exp_req', sa.String(length=50), nullable=True),
    sa.Column('professional_test', sa.String(length=50), nullable=True),
    sa.Column('interview_ratio', sa.String(length=50), nullable=True),
    sa.Column('work_location', sa.String(length=200), nullable=True),
    sa.Column('settle_location', sa.String(length=200), nullable=True),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('dept_website', sa.String(length=200), nullable=True),
    sa.Column('phone1', sa.String(length=50), nullable=True),
    sa.Column('phone2', sa.String(length=50), nullable=True),
    sa.Column('phone3', sa.String(length=50), nullable=True),
    sa.Column('sheet_name', sa.String(length=50), nullable=True),
    sa.Column('source_url', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('gwy_position', schema=None) as batch_op:
        batch_op.create_index('ix_gwy_position_year_code', ['year', 'position_code'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('gwy_position', schema=None) as batch_op:
        batch_op.drop_index('ix_gwy_position_year_code')

    op.drop_table('gwy_position')
