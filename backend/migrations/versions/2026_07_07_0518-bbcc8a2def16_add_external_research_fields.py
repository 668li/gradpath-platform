"""add_external_research_fields

Revision ID: bbcc8a2def16
Revises: add_mentor_tables
Create Date: 2026-07-07 05:18:02.630098+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "bbcc8a2def16"
down_revision: Union[str, None] = "add_mentor_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create kaoyan_news table
    op.create_table(
        "kaoyan_news",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("source_platform", sa.String(length=50), nullable=False, server_default="rss"),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "crawled_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="general"),
        sa.Column("tags", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url"),
    )
    with op.batch_alter_table("kaoyan_news", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_kaoyan_news_category"), ["category"], unique=False)
        batch_op.create_index(batch_op.f("ix_kaoyan_news_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_kaoyan_news_title"), ["title"], unique=False)

    # Add external platform counters to experience_posts
    with op.batch_alter_table("experience_posts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("external_view_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("external_like_count", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("experience_posts", schema=None) as batch_op:
        batch_op.drop_column("external_like_count")
        batch_op.drop_column("external_view_count")

    with op.batch_alter_table("kaoyan_news", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_kaoyan_news_title"))
        batch_op.drop_index(batch_op.f("ix_kaoyan_news_status"))
        batch_op.drop_index(batch_op.f("ix_kaoyan_news_category"))

    op.drop_table("kaoyan_news")
