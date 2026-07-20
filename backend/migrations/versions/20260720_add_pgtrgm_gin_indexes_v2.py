"""扩展 pg_trgm GIN 索引覆盖到 schools/companies/posts/mentors/skills 表

Revision ID: add_pgtrgm_gin_indexes_v2
Revises: add_notification_link
Create Date: 2026-07-20

阶段 4 A13：补充 GIN trgm 索引覆盖原 LIKE 搜索字段：
- schools.name
- companies.name
- posts.title / posts.content
- mentors.name
- skill_nodes.name

schools.major 字段在模型中不存在（用 key_majors JSONB 存储专业列表），
故跳过；experience_posts / knowledge_articles / qas / dark_knowledge 已在
add_pgtrgm_gin_indexes 迁移中覆盖。
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op


revision: str = "add_pgtrgm_gin_indexes_v2"
down_revision: Union[str, None] = "add_notification_link"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 阶段 4 A13：补充 GIN trgm 索引覆盖字段
# 索引名规范：idx_<table>_<column>_trgm
TABLES_AND_COLUMNS = [
    ("schools", "name"),
    ("companies", "name"),
    ("posts", "title"),
    ("posts", "content"),
    ("mentors", "name"),
    ("skill_nodes", "name"),
]


def _is_postgresql() -> bool:
    """检测当前连接是否为 PostgreSQL。"""
    bind = op.get_bind()
    return "postgresql" in str(bind.engine.url)


def upgrade() -> None:
    if _is_postgresql():
        # 启用 pg_trgm 扩展（幂等）
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        for table, column in TABLES_AND_COLUMNS:
            index_name = f"idx_{table}_{column}_trgm"
            sql = (
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                f"ON {table} USING GIN ({column} gin_trgm_ops)"
            )
            op.execute(sql)


def downgrade() -> None:
    if _is_postgresql():
        for table, column in TABLES_AND_COLUMNS:
            index_name = f"idx_{table}_{column}_trgm"
            op.execute(f"DROP INDEX IF EXISTS {index_name}")
