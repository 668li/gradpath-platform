"""添加导师评价系统表

Revision ID: add_mentor_tables
Revises:
Create Date: 2026-03-18

添加两个新表：
- mentors: 导师主表
- mentor_reviews: 导师评价表
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_mentor_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 mentors 表
    op.create_table(
        "mentors",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("university", sa.String(length=200), nullable=False),
        sa.Column("department", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("research_directions", sa.JSON(), nullable=False),
        sa.Column("paper_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("project_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("h_index", sa.Integer(), nullable=True),
        sa.Column("academic_homepage", sa.String(length=500), nullable=True),
        sa.Column("google_scholar_url", sa.String(length=500), nullable=True),
        sa.Column("cnki_url", sa.String(length=500), nullable=True),
        sa.Column("enrollment_status", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("enrollment_directions", sa.JSON(), nullable=False),
        sa.Column("contact_email", sa.String(length=200), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("avg_rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_academic", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rating_guidance", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rating_relationship", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rating_funding", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rating_workload", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rating_career", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_platform", sa.String(length=100), nullable=False, server_default="official"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 创建索引
    op.create_index(op.f("ix_mentors_name"), "mentors", ["name"], unique=False)
    op.create_index(op.f("ix_mentors_university"), "mentors", ["university"], unique=False)
    op.create_index(op.f("ix_mentors_department"), "mentors", ["department"], unique=False)

    # 创建 mentor_reviews 表
    op.create_table(
        "mentor_reviews",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("mentor_id", sa.String(32), nullable=False),
        sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("anonymous_id", sa.String(length=50), nullable=True),
        sa.Column("rating_academic", sa.Integer(), nullable=False),
        sa.Column("rating_guidance", sa.Integer(), nullable=False),
        sa.Column("rating_relationship", sa.Integer(), nullable=False),
        sa.Column("rating_funding", sa.Integer(), nullable=False),
        sa.Column("rating_workload", sa.Integer(), nullable=False),
        sa.Column("rating_career", sa.Integer(), nullable=False),
        sa.Column("overall_rating", sa.Float(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("pros", sa.JSON(), nullable=False),
        sa.Column("cons", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_helpful", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("submitted_at", sa.String(length=50), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verification_proof", sa.String(length=500), nullable=True),
        sa.Column("reviewer_identity", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mentor_id"], ["mentors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 创建索引
    op.create_index(op.f("ix_mentor_reviews_mentor_id"), "mentor_reviews", ["mentor_id"], unique=False)
    op.create_index(op.f("ix_mentor_reviews_user_id"), "mentor_reviews", ["user_id"], unique=False)
    op.create_index(op.f("ix_mentor_reviews_review_status"), "mentor_reviews", ["review_status"], unique=False)


def downgrade() -> None:
    op.drop_table("mentor_reviews")
    op.drop_table("mentors")
