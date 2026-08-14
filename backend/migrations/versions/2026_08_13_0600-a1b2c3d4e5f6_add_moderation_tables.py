"""add moderation tables: reports / block_relations, ban fields on users, post visibility

Revision ID: a1b2c3d4e5f6
Revises: efc46b02f792
Create Date: 2026-08-13

社区治理（成熟化补齐 Phase A1）：
- users 加 status(active/banned) / banned_at / ban_reason（封禁）
- posts 加 status(active/hidden)（举报处理下架）
- 新表 reports（内容/用户举报）、block_relations（用户屏蔽）

升级：加列与建表均幂等（存在则跳过），兼容 fresh 与存量库。
降级：仅当存在时才删除。
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "efc46b02f792"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())

    # --- users: 封禁字段（server_default 兼容存量行；SQLite 加列必须带默认或可空） ---
    if "users" in tables:
        cols = _existing_columns("users")
        if "status" not in cols:
            op.add_column(
                "users",
                sa.Column(
                    "status",
                    sa.Enum("active", "banned", name="userstatus"),
                    nullable=False,
                    server_default="active",
                    comment="账户状态: active/banned",
                ),
            )
        if "banned_at" not in cols:
            op.add_column(
                "users",
                sa.Column("banned_at", sa.DateTime(timezone=True), nullable=True, comment="封禁时间"),
            )
        if "ban_reason" not in cols:
            op.add_column(
                "users",
                sa.Column("ban_reason", sa.String(length=500), nullable=True, comment="封禁原因"),
            )

    # --- posts: 可见性（举报下架） ---
    if "posts" in tables:
        cols = _existing_columns("posts")
        if "status" not in cols:
            op.add_column(
                "posts",
                sa.Column(
                    "status",
                    sa.Enum("active", "hidden", name="poststatus"),
                    nullable=False,
                    server_default="active",
                    comment="可见性: active/hidden",
                ),
            )

    # --- reports 表 ---
    if "reports" not in tables:
        op.create_table(
            "reports",
            sa.Column("id", sa.String(length=32), primary_key=True),
            sa.Column("reporter_id", sa.String(length=32), nullable=False),
            sa.Column(
                "target_type",
                sa.Enum(
                    "post", "experience_post", "comment", "qa", "qa_answer", "user",
                    name="reporttargettype",
                ),
                nullable=False,
            ),
            sa.Column("target_id", sa.String(length=64), nullable=False),
            sa.Column("reason", sa.String(length=100), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column(
                "status",
                sa.Enum("pending", "processed", "rejected", name="reportstatus"),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("processed_by", sa.String(length=32), nullable=True),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("processed_note", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["reporter_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["processed_by"], ["users.id"]),
        )
        op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"])
        op.create_index("ix_reports_status_created", "reports", ["status", "created_at"])
        op.create_index("ix_reports_target", "reports", ["target_type", "target_id"])

    # --- block_relations 表 ---
    if "block_relations" not in tables:
        op.create_table(
            "block_relations",
            sa.Column("id", sa.String(length=32), primary_key=True),
            sa.Column("blocker_id", sa.String(length=32), nullable=False),
            sa.Column("blocked_id", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["blocker_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["blocked_id"], ["users.id"]),
            sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_block_relation_pair"),
        )
        op.create_index("ix_block_relations_blocker_id", "block_relations", ["blocker_id"])
        op.create_index("ix_block_relations_blocked_id", "block_relations", ["blocked_id"])


def downgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())

    if "block_relations" in tables:
        op.drop_table("block_relations")
    if "reports" in tables:
        op.drop_table("reports")
    if "posts" in tables:
        cols = _existing_columns("posts")
        if "status" in cols:
            op.drop_column("posts", "status")
    if "users" in tables:
        cols = _existing_columns("users")
        for col in ("ban_reason", "banned_at", "status"):
            if col in cols:
                op.drop_column("users", col)
