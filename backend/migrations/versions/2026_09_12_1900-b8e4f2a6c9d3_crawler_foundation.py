"""爬虫地基（spec 002）：线状态表 + 三态证据列。

数据地基④⑥：t_crawler_source_state（增量游标/连续失败/隔离位）。
数据地基⑤：t_external_research_item 增 data_origin（fetched/curated/ugc/legacy，
存量回填 legacy 冻结）与 fetch_evidence（fetched 态必带 http_status/fetched_at/sha256）。
down_revision 实证生产 alembic current=f1a3b5c7d9e2（09-12 topology 实锤），禁幻影 stamp。

Revision ID: b8e4f2a6c9d3
Revises: f1a3b5c7d9e2
Create Date: 2026-09-12 19:00:00.000000+00:00

Revision 链：… → c8d4e6f2a9b1 → f1a3b5c7d9e2 → b8e4f2a6c9d3（单头线性）。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import JSONB

# revision identifiers, used by Alembic.
revision: str = "b8e4f2a6c9d3"
down_revision: Union[str, None] = "f1a3b5c7d9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "t_crawler_source_state",
        sa.Column("source_name", sa.String(length=50), nullable=False),
        sa.Column("cursor", JSONB(), nullable=True),
        sa.Column("etag", sa.String(length=128), nullable=True),
        sa.Column("last_modified", sa.String(length=64), nullable=True),
        sa.Column("last_ok_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("consecutive_fails", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("isolated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("isolated_reason", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("source_name", name=op.f("pk_t_crawler_source_state")),
    )

    op.add_column(
        "t_external_research_item",
        sa.Column("data_origin", sa.String(length=12), nullable=True),
    )
    op.add_column(
        "t_external_research_item",
        sa.Column("fetch_evidence", JSONB(), nullable=True),
    )
    # 存量冻结（蓝图 C5）：没有抓取证据的历史数据一律打 legacy 标，新写入禁用该态
    op.execute("UPDATE t_external_research_item SET data_origin = 'legacy' WHERE data_origin IS NULL")
    op.create_index(
        "idx_external_research_item_data_origin",
        "t_external_research_item",
        ["data_origin"],
    )


def downgrade() -> None:
    op.drop_index("idx_external_research_item_data_origin", table_name="t_external_research_item")
    op.drop_column("t_external_research_item", "fetch_evidence")
    op.drop_column("t_external_research_item", "data_origin")
    op.drop_table("t_crawler_source_state")
