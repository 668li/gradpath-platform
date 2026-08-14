"""create data_freshness table

Revision ID: df1a2b3c4d5e
Revises: a1b2c3d4e5f6
Create Date: 2026-08-13 09:00:00.000000+00:00

B4：data_freshness 引擎此前只有 API 与 raw SQL（表不存在时降级返回空），
补建表使其可真正记录来源新鲜度；审核 confirm 入库时由 research_promote 回写
（见 _touch_data_freshness）。列契约与 app/api/data_freshness.py 的 raw SQL 一致：
- source_name 主键（渠道名，对应 SOURCES 字典键）
- last_successful_crawl 最近一次成功抓取/确认时间
- records_count 累计确认入库条数
- status active / refreshing / unknown
- updated_at 回写时间
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df1a2b3c4d5e'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'data_freshness',
        sa.Column('source_name', sa.String(50), primary_key=True),
        sa.Column('last_successful_crawl', sa.DateTime(), nullable=True),
        sa.Column('records_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('data_freshness')
