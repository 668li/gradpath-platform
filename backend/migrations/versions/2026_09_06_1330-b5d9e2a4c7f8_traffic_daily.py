"""站点流量日聚合表 t_traffic_daily —— /admin/traffic 流量看板数据源。

口径与微信日报 visitors.sh 一致：pv/uv/blocked 由宿主侧
monitoring/traffic_pipeline.sh 从 nginx 日志聚合（机器人已滤、444 单列、
轮询心跳不计），registrations 来自 users 表按北京时间日聚合。
幂等 upsert，当日行为部分快照、次日起稳定。

Revision ID: b5d9e2a4c7f8
Revises: e7f8a9b0c1d2
Create Date: 2026-09-06 13:30
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b5d9e2a4c7f8"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "t_traffic_daily",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("pv", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uv", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("registrations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("date"),
    )


def downgrade() -> None:
    op.drop_table("t_traffic_daily")
