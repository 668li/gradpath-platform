"""添加性能优化索引

Revision ID: add_perf_indexes
Revises: add_mentor_tables
Create Date: 2026-07-16

添加复合索引优化查询性能：
- schools: province + level 复合索引
- dark_knowledge: stage + category 复合索引
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_perf_indexes"
down_revision: Union[str, None] = "add_mentor_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # schools 表: province + level 复合索引
    # 用于按省份和层次筛选院校的查询
    op.create_index(
        "ix_school_province_level",
        "schools",
        ["province", "level"],
        unique=False,
    )

    # dark_knowledge 表: stage + category 复合索引
    # 用于按阶段和分类查询暗知识
    op.create_index(
        "ix_dark_knowledge_stage_category",
        "dark_knowledge",
        ["stage", "category"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dark_knowledge_stage_category", table_name="dark_knowledge")
    op.drop_index("ix_school_province_level", table_name="schools")
