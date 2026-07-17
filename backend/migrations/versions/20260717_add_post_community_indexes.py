"""添加 Post 和 CommunityReport 模型索引

Revision ID: add_post_community_indexes
Revises: add_pgtrgm_gin_indexes
Create Date: 2026-07-17

添加索引：
- posts: topic_type + topic_key 复合索引，topic_key/user_id/parent_id 单列索引
- community_reports: school_name/major/graduation_year/destination_type 单列索引
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_post_community_indexes"
down_revision: Union[str, None] = "add_pgtrgm_gin_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # posts 表: 复合索引 topic_type + topic_key（社区讨论区高频查询入口）
    op.create_index(
        "ix_posts_topic_type_key",
        "posts",
        ["topic_type", "topic_key"],
        unique=False,
    )
    # posts 表: topic_key 单列索引
    op.create_index(
        "ix_posts_topic_key",
        "posts",
        ["topic_key"],
        unique=False,
    )
    # posts 表: user_id 索引（用户发帖历史）
    op.create_index(
        "ix_posts_user_id",
        "posts",
        ["user_id"],
        unique=False,
    )
    # posts 表: parent_id 索引（查询回复列表）
    op.create_index(
        "ix_posts_parent_id",
        "posts",
        ["parent_id"],
        unique=False,
    )

    # community_reports 表: school_name 索引（聚合过滤条件）
    op.create_index(
        "ix_community_reports_school_name",
        "community_reports",
        ["school_name"],
        unique=False,
    )
    # community_reports 表: major 索引（聚合过滤条件）
    op.create_index(
        "ix_community_reports_major",
        "community_reports",
        ["major"],
        unique=False,
    )
    # community_reports 表: graduation_year 索引（聚合过滤条件）
    op.create_index(
        "ix_community_reports_graduation_year",
        "community_reports",
        ["graduation_year"],
        unique=False,
    )
    # community_reports 表: destination_type 索引（group by 去向类型分布）
    op.create_index(
        "ix_community_reports_destination_type",
        "community_reports",
        ["destination_type"],
        unique=False,
    )


def downgrade() -> None:
    # community_reports 索引
    op.drop_index("ix_community_reports_destination_type", table_name="community_reports")
    op.drop_index("ix_community_reports_graduation_year", table_name="community_reports")
    op.drop_index("ix_community_reports_major", table_name="community_reports")
    op.drop_index("ix_community_reports_school_name", table_name="community_reports")

    # posts 索引
    op.drop_index("ix_posts_parent_id", table_name="posts")
    op.drop_index("ix_posts_user_id", table_name="posts")
    op.drop_index("ix_posts_topic_key", table_name="posts")
    op.drop_index("ix_posts_topic_type_key", table_name="posts")