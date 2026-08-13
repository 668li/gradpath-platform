"""对齐 users 表 bio / avatar_url 字段与模型

Revision ID: b90c8dd58221
Revises: e5a9c2f4b7d1
Create Date: 2026-08-12

users 模型（app/models/user.py）含 bio(String(500), nullable) 与
avatar_url(String(500), nullable)，但 9c43ddf069ce 完整快照的 users 表缺失这两列。
本迁移在快照之上补齐，使 `alembic check`（模型 vs 库）零漂移。

升级：仅当 users 表存在且列缺失时才 ALTER（幂等）。
降级：仅当列存在时才 DROP（幂等）。
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "b90c8dd58221"
down_revision: Union[str, None] = "e5a9c2f4b7d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "users" not in tables:
        return
    cols = _existing_columns("users")
    if "bio" not in cols:
        op.add_column(
            "users",
            sa.Column("bio", sa.String(length=500), nullable=True, comment="用户个人简介"),
        )
    if "avatar_url" not in cols:
        op.add_column(
            "users",
            sa.Column("avatar_url", sa.String(length=500), nullable=True, comment="用户头像 URL"),
        )


def downgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "users" not in tables:
        return
    cols = _existing_columns("users")
    if "avatar_url" in cols:
        op.drop_column("users", "avatar_url")
    if "bio" in cols:
        op.drop_column("users", "bio")
