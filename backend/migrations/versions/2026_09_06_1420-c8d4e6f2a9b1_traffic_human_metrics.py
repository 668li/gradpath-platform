"""站点流量日聚合表新增真人口径四列 —— /admin/traffic 看板"实际真的"数据。

09-06 用户拍板"要实际真的，不是假的"：uv/pv 原口径混入伪装扫描器（zgrab/censys/
zmap/bytespider 等无 bot 字样的 UA）与挂机心跳。新四列由 traffic_pipeline.sh
行为分类（UA 真实浏览器 + 打开过页面 + 心跳剔除）产出：
- human_uv / human_pv：真人数 / 真人页面浏览
- machine_uv：剔除的脚本来源数
- single_uv：单次来源数（无法判定真人或脚本，单列不计入真人）

Revision ID: c8d4e6f2a9b1
Revises: b5d9e2a4c7f8
Create Date: 2026-09-06 14:20
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c8d4e6f2a9b1"
down_revision = "b5d9e2a4c7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for col in ("human_uv", "human_pv", "machine_uv", "single_uv"):
        op.add_column("t_traffic_daily", sa.Column(col, sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    for col in ("single_uv", "machine_uv", "human_pv", "human_uv"):
        op.drop_column("t_traffic_daily", col)
