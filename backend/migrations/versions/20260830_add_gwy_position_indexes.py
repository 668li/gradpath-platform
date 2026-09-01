"""gwy_position 性能索引：高频过滤列 btree + 模糊搜索 pg_trgm GIN

Revision ID: add_gwy_pos_indexes
Revises: c8e4f2a91b27
Create Date: 2026-08-30

列表页（/api/gwy-positions）与决策引擎的高频查询路径：
- btree：education_req / political_status / org_level / exam_category 为等值过滤，
  work_location 为前缀 LIKE（'广东%'），均可走 btree。
- pg_trgm GIN：major_req / position_name / dept_name 为 '%关键词%' 模糊匹配
  （btree 无法命中），索引名规范 idx_<table>_<column>_trgm
  （tests/test_pg_trgm_search.py 强制校验命名）。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "add_gwy_pos_indexes"
down_revision: Union[str, None] = "c8e4f2a91b27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BTREE_INDEXES = [
    ("ix_gwy_position_education_req", "education_req"),
    ("ix_gwy_position_political_status", "political_status"),
    ("ix_gwy_position_org_level", "org_level"),
    ("ix_gwy_position_exam_category", "exam_category"),
    ("ix_gwy_position_work_location", "work_location"),
]


def _has_table(name: str) -> bool:
    return name in set(inspect(op.get_bind()).get_table_names())


def _is_postgresql() -> bool:
    """检测当前连接是否为 PostgreSQL。"""
    bind = op.get_bind()
    return "postgresql" in str(bind.engine.url)


def upgrade() -> None:
    if not _has_table("gwy_position"):
        return
    for index_name, column in BTREE_INDEXES:
        op.create_index(index_name, "gwy_position", [column], unique=False)
    if _is_postgresql():
        # 启用 pg_trgm 扩展（幂等）
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        # GIN trgm 索引（固定 DDL 字面量；索引名规范 idx_<table>_<column>_trgm）
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_gwy_position_major_req_trgm"
            " ON gwy_position USING GIN (major_req gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_gwy_position_position_name_trgm"
            " ON gwy_position USING GIN (position_name gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_gwy_position_dept_name_trgm"
            " ON gwy_position USING GIN (dept_name gin_trgm_ops)"
        )


def downgrade() -> None:
    if not _has_table("gwy_position"):
        return
    if _is_postgresql():
        op.execute("DROP INDEX IF EXISTS idx_gwy_position_major_req_trgm")
        op.execute("DROP INDEX IF EXISTS idx_gwy_position_position_name_trgm")
        op.execute("DROP INDEX IF EXISTS idx_gwy_position_dept_name_trgm")
    for index_name, _column in BTREE_INDEXES:
        op.drop_index(index_name, table_name="gwy_position")
