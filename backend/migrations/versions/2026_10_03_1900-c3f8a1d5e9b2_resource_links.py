"""资源导航链接表（RN-1，2026-10-03 任务书：资源导航聚合中心）。

新建 resource_links：目录条目 = 链接 + 一句话定位 + 实测记录（零搬运）。
全站公共目录（无 user_id 列），镜像 intel_cards 形态。
不含任何枚举类型（track/category/copyright_tier/status/added_via 均为
String 列+应用层常量约束），规避枚举预创建自伤雷（2026-09-25 教训，照抄 b5d9 注释）。

点名制约束落在表结构上：user_approved 默认 false，应用层禁自动置 true。

downgrade 忠实回滚：drop resource_links。

Revision 链：… → b5d9e2c4a7f1 → c3f8a1d5e9b2（单头线性）。

Revision ID: c3f8a1d5e9b2
Revises: b5d9e2c4a7f1
Create Date: 2026-10-03 19:00:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "c3f8a1d5e9b2"
down_revision: Union[str, None] = "b5d9e2c4a7f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resource_links",
        sa.Column("id", GUID(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("track", sa.String(20), nullable=False, server_default="kaoyan"),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("note", sa.String(300), nullable=False),
        sa.Column("risk_note", sa.String(300), nullable=True),
        sa.Column("copyright_tier", sa.String(20), nullable=False, server_default="original"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("added_via", sa.String(20), nullable=False, server_default="ai_research"),
        sa.Column("user_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sources", JSONB(), nullable=False),
        sa.Column("recently_added", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_resource_links_url", "resource_links", ["url"], unique=True)
    op.create_index("ix_resource_links_track", "resource_links", ["track"])
    op.create_index("ix_resource_links_category", "resource_links", ["category"])
    op.create_index("ix_resource_links_status", "resource_links", ["status"])


def downgrade() -> None:
    op.drop_index("ix_resource_links_status", table_name="resource_links")
    op.drop_index("ix_resource_links_category", table_name="resource_links")
    op.drop_index("ix_resource_links_track", table_name="resource_links")
    op.drop_index("ix_resource_links_url", table_name="resource_links")
    op.drop_table("resource_links")
