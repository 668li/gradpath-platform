"""add_external_research_fields

Revision ID: bbcc8a2def16
Revises: add_mentor_tables
Create Date: 2026-07-07 05:18:02.630098+00:00

注意：本迁移的建表/加列职责已由 9c43ddf069ce（autogenerate 完整快照）统一承担：
- kaoyan_news 由快照 line 258 创建（含 uk_source_url + 3 索引）
- experience_posts 由快照 line 773 创建，且已含 external_view_count / external_like_count 列
从零升级时空库由快照建表即可；历史增量库该 revision 早已 stamp 不会重跑。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "bbcc8a2def16"
down_revision: Union[str, None] = "add_mentor_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 不再重复建表/加列：kaoyan_news 与 experience_posts 的外部计数字段
    # 均由 9c43ddf069ce 快照统一创建，此处 no-op。
    return


def downgrade() -> None:
    # 与 upgrade 对称：从零库 downgrade 时这两张表/列已先被 9c43ddf069ce 的
    # downgrade 删除，这里仅当目标存在才执行，避免「表/列不存在」报错。
    existing = set(inspect(op.get_bind()).get_table_names())
    if "kaoyan_news" in existing:
        with op.batch_alter_table("kaoyan_news", schema=None) as batch_op:
            batch_op.drop_index(batch_op.f("ix_kaoyan_news_title"))
            batch_op.drop_index(batch_op.f("ix_kaoyan_news_status"))
            batch_op.drop_index(batch_op.f("ix_kaoyan_news_category"))
        op.drop_table("kaoyan_news")
    if "experience_posts" in existing:
        with op.batch_alter_table("experience_posts", schema=None) as batch_op:
            batch_op.drop_column("external_like_count")
            batch_op.drop_column("external_view_count")
