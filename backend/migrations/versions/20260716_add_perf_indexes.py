"""添加性能优化索引

Revision ID: add_perf_indexes
Revises: add_mentor_tables
Create Date: 2026-07-16

添加复合索引优化查询性能：
- schools: province + level 复合索引
- dark_knowledge: stage + category 复合索引

从零升级：schools / dark_knowledge 由 9c43ddf069ce 快照创建（快照内已含
ix_school_province_level / ix_dark_knowledge_stage_category 索引），
故仅当目标表已存在（历史增量库补建索引场景）才执行。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "add_perf_indexes"
down_revision: Union[str, None] = "add_mentor_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    # schools 表: province + level 复合索引（用于按省份和层次筛选院校）
    if _has_table("schools"):
        op.create_index(
            "ix_school_province_level",
            "schools",
            ["province", "level"],
            unique=False,
        )
    # dark_knowledge 表: stage + category 复合索引（用于按阶段和分类查询暗知识）
    if _has_table("dark_knowledge"):
        op.create_index(
            "ix_dark_knowledge_stage_category",
            "dark_knowledge",
            ["stage", "category"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("dark_knowledge"):
        op.drop_index("ix_dark_knowledge_stage_category", table_name="dark_knowledge")
    if _has_table("schools"):
        op.drop_index("ix_school_province_level", table_name="schools")
