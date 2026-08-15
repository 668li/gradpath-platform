"""add gwy_province_position table

Revision ID: 8bff65fa26e8
Revises: 9341ee5f3e2a
Create Date: 2026-08-14 09:31:11.060048+00:00

注：autogenerate 曾带入历史 create_all+stamp 漂移（20+ 张旧表），已手动裁剪为仅目标表。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8bff65fa26e8'
down_revision: Union[str, None] = '9341ee5f3e2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('gwy_province_position',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('province', sa.String(length=20), nullable=False),
    sa.Column('dept_name', sa.String(length=200), nullable=True),
    sa.Column('dept_code', sa.String(length=50), nullable=True),
    sa.Column('position_name', sa.String(length=200), nullable=True),
    sa.Column('position_code', sa.String(length=50), nullable=False),
    sa.Column('position_desc', sa.Text(), nullable=True),
    sa.Column('position_type', sa.String(length=100), nullable=True),
    sa.Column('recruit_count', sa.Integer(), nullable=True),
    sa.Column('education_req', sa.String(length=100), nullable=True),
    sa.Column('degree_req', sa.String(length=100), nullable=True),
    sa.Column('major_req_grad', sa.Text(), nullable=True),
    sa.Column('major_req_undergrad', sa.Text(), nullable=True),
    sa.Column('major_req_junior', sa.Text(), nullable=True),
    sa.Column('grassroots_exp_req', sa.String(length=10), nullable=True),
    sa.Column('psych_test', sa.String(length=10), nullable=True),
    sa.Column('fresh_grad_only', sa.String(length=10), nullable=True),
    sa.Column('other_requirements', sa.Text(), nullable=True),
    sa.Column('exam_region', sa.String(length=50), nullable=True),
    sa.Column('sheet_name', sa.String(length=50), nullable=True),
    sa.Column('source_url', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('gwy_province_position', schema=None) as batch_op:
        batch_op.create_index('ix_gwy_province_position_year_prov_code', ['year', 'province', 'position_code'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('gwy_province_position', schema=None) as batch_op:
        batch_op.drop_index('ix_gwy_province_position_year_prov_code')

    op.drop_table('gwy_province_position')
