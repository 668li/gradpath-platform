"""添加pg_trgm GIN索引优化全文搜索

Revision ID: add_pgtrgm_gin_indexes
Revises: add_perf_indexes
Create Date: 2026-07-17

- PostgreSQL: 启用 pg_trgm 扩展，为搜索字段创建 GIN 索引（加速 ILIKE '%term%' 查询）
- SQLite: 跳过 GIN 索引（不支持），添加 B-tree 索引供 LIKE 查询部分优化
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op

revision: str = "add_pgtrgm_gin_indexes"
down_revision: Union[str, None] = "add_perf_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# GIN trgm 索引：仅 PostgreSQL 生效，加速 ILIKE '%keyword%' 全文搜索
TABLES_AND_COLUMNS = [
    ("experience_posts", "title"),
    ("experience_posts", "content"),
    ("knowledge_articles", "title"),
    ("knowledge_articles", "content"),
    ("qas", "title"),
    ("qas", "content"),
    ("dark_knowledge", "title"),
    ("dark_knowledge", "content"),
]


def _is_postgresql() -> bool:
    """检测当前连接是否为 PostgreSQL。"""
    bind = op.get_bind()
    return "postgresql" in str(bind.engine.url)


def upgrade() -> None:
    if _is_postgresql():
        # 启用 pg_trgm 扩展（支持三字母组 GIN 索引）
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        for table, column in TABLES_AND_COLUMNS:
            index_name = f"ix_{table}_{column}_trgm"
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} USING GIN ({column} gin_trgm_ops)"
            op.execute(sql)

    # B-tree 索引（兼容所有数据库）：加速 WHERE 过滤条件
    # knowledge_articles.is_published 用于搜索 WHERE 子句，但缺少索引
    op.create_index(
        "ix_knowledge_articles_is_published",
        "knowledge_articles",
        ["is_published"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_articles_is_published", table_name="knowledge_articles")
    if _is_postgresql():
        for table, column in TABLES_AND_COLUMNS:
            index_name = f"ix_{table}_{column}_trgm"
            op.execute(f"DROP INDEX IF EXISTS {index_name}")
