"""add action/growth/review/ingestion contract tables

Revision ID: e5a9c2f4b7d1
Revises: c4d2e6f8a1b3
Create Date: 2026-08-12 00:00:00.000000+00:00

方案 C「契约先行」10 张新表落库（系统设计 §4.2.1 ~ §4.2.10）：
- 行动任务中心：t_action / t_action_checkin / t_action_streak / t_action_weight
- 成长档案中心：t_growth_trajectory / t_growth_archive
- 复盘中心：t_review_record
- 数据真实性接入层：t_data_source / t_external_research_item / t_review_queue_item

另为 crawler_runs 补充契约扩展字段（§4.2.11）：
stored_count / duplicate_count / source_meta。

字段严格对齐 app/models 下对应契约模型（含 server_default 与索引/唯一键），
保证 alembic check（autogenerate 零漂移）。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

import app.models.base

# revision identifiers, used by Alembic.
revision: str = "e5a9c2f4b7d1"
down_revision: Union[str, None] = "c4d2e6f8a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _bigint_pk() -> sa.BigInteger:
    """跨方言 BIGINT 自增主键，等价于 app.models.base.BigIntPK。"""
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    # ===== 行动任务中心（§4.2.1 ~ §4.2.4）=====
    op.create_table(
        "t_action",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("action_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("source_decision_id", sa.BigInteger(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("biz_req_no", sa.String(length=64), nullable=True),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "action_type", "due_date", name="uk_action_user_id_action_type_due_date"),
    )
    with op.batch_alter_table("t_action", schema=None) as batch_op:
        batch_op.create_index("idx_action_user_id_due_date", ["user_id", "due_date"], unique=False)
        batch_op.create_index("idx_action_user_id_status", ["user_id", "status"], unique=False)

    op.create_table(
        "t_action_checkin",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("action_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("evidence_url", sa.String(length=500), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("biz_req_no", sa.String(length=64), nullable=False),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("biz_req_no", name="uk_action_checkin_biz_req_no"),
    )
    with op.batch_alter_table("t_action_checkin", schema=None) as batch_op:
        batch_op.create_index("idx_action_checkin_action_id", ["action_id"], unique=False)
        batch_op.create_index("idx_action_checkin_user_id_completed_at", ["user_id", "completed_at"], unique=False)

    op.create_table(
        "t_action_streak",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("current_streak_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("longest_streak_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_checkin_date", sa.Date(), nullable=True),
        sa.Column("streak_status", sa.String(length=20), nullable=False, server_default=sa.text("'NEVER'")),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uk_action_streak_user_id"),
    )

    op.create_table(
        "t_action_weight",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("action_type", sa.String(length=20), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("weight_label", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("action_type", name="uk_action_weight_action_type"),
    )

    # ===== 成长档案中心（§4.2.5 ~ §4.2.6）=====
    op.create_table(
        "t_growth_trajectory",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("event_payload", app.models.base.JSONB(), nullable=False),
        sa.Column("source_event_id", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_event_id", name="uk_growth_trajectory_source_event_id"),
    )
    with op.batch_alter_table("t_growth_trajectory", schema=None) as batch_op:
        batch_op.create_index("idx_growth_trajectory_user_id_occurred_at", ["user_id", "occurred_at"], unique=False)

    op.create_table(
        "t_growth_archive",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("action_completion_rate", sa.Numeric(precision=5, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("total_actions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_actions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("weighted_action_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("archive_status", sa.String(length=20), nullable=False, server_default=sa.text("'ACTIVE'")),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uk_growth_archive_user_id"),
    )

    # ===== 复盘中心（§4.2.7）=====
    op.create_table(
        "t_review_record",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("review_type", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("action_refs", app.models.base.JSONB(), nullable=True),
        sa.Column("mood_score", sa.Integer(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_insights", app.models.base.JSONB(), nullable=True),
        sa.Column("ai_suggestions", app.models.base.JSONB(), nullable=True),
        sa.Column("uncertainty_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("biz_req_no", sa.String(length=64), nullable=True),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("t_review_record", schema=None) as batch_op:
        batch_op.create_index("idx_review_record_user_id_period", ["user_id", "period_start", "period_end"], unique=False)
        batch_op.create_index("idx_review_record_user_id_status", ["user_id", "status"], unique=False)

    # ===== 数据真实性接入层（§4.2.8 ~ §4.2.10）=====
    op.create_table(
        "t_data_source",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("source_system", sa.String(length=30), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("crawled_at", sa.DateTime(), nullable=False),
        sa.Column("credibility", sa.String(length=20), nullable=False, server_default=sa.text("'model_inferred'")),
        sa.Column("verify_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("reviewed_by", sa.String(length=64), nullable=True),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url", name="uk_data_source_source_url"),
    )
    with op.batch_alter_table("t_data_source", schema=None) as batch_op:
        batch_op.create_index("idx_data_source_credibility", ["credibility"], unique=False)
        batch_op.create_index("idx_data_source_review_status", ["review_status"], unique=False)

    op.create_table(
        "t_external_research_item",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("crawler_name", sa.String(length=50), nullable=False),
        sa.Column("crawler_run_id", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("source_platform", sa.String(length=30), nullable=False),
        sa.Column("external_meta", app.models.base.JSONB(), nullable=True),
        sa.Column("credibility", sa.String(length=20), nullable=False, server_default=sa.text("'model_inferred'")),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url", name="uk_external_research_item_source_url"),
    )
    with op.batch_alter_table("t_external_research_item", schema=None) as batch_op:
        batch_op.create_index("idx_external_research_item_crawler_run_id", ["crawler_run_id"], unique=False)
        batch_op.create_index("idx_external_research_item_review_status", ["review_status"], unique=False)

    op.create_table(
        "t_review_queue_item",
        sa.Column("id", _bigint_pk(), autoincrement=True, nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("ref_item_id", sa.BigInteger(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("reviewed_by", sa.String(length=64), nullable=True),
        sa.Column("reviewed_time", sa.DateTime(), nullable=True),
        sa.Column("reject_reason", sa.String(length=500), nullable=True),
        sa.Column("biz_req_no", sa.String(length=64), nullable=False),
        # ContractAuditMixin
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_time", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("biz_req_no", name="uk_review_queue_item_biz_req_no"),
    )
    with op.batch_alter_table("t_review_queue_item", schema=None) as batch_op:
        batch_op.create_index("idx_review_queue_item_status_created_time", ["review_status", "created_time"], unique=False)
        batch_op.create_index("idx_review_queue_item_type_ref", ["item_type", "ref_item_id"], unique=False)

    # ===== crawler_runs 契约扩展字段（§4.2.11）=====
    with op.batch_alter_table("crawler_runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("stored_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("source_meta", app.models.base.JSONB(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("crawler_runs", schema=None) as batch_op:
        batch_op.drop_column("source_meta")
        batch_op.drop_column("duplicate_count")
        batch_op.drop_column("stored_count")

    with op.batch_alter_table("t_review_queue_item", schema=None) as batch_op:
        batch_op.drop_index("idx_review_queue_item_type_ref")
        batch_op.drop_index("idx_review_queue_item_status_created_time")
    op.drop_table("t_review_queue_item")

    with op.batch_alter_table("t_external_research_item", schema=None) as batch_op:
        batch_op.drop_index("idx_external_research_item_review_status")
        batch_op.drop_index("idx_external_research_item_crawler_run_id")
    op.drop_table("t_external_research_item")

    with op.batch_alter_table("t_data_source", schema=None) as batch_op:
        batch_op.drop_index("idx_data_source_review_status")
        batch_op.drop_index("idx_data_source_credibility")
    op.drop_table("t_data_source")

    with op.batch_alter_table("t_review_record", schema=None) as batch_op:
        batch_op.drop_index("idx_review_record_user_id_status")
        batch_op.drop_index("idx_review_record_user_id_period")
    op.drop_table("t_review_record")

    op.drop_table("t_growth_archive")

    with op.batch_alter_table("t_growth_trajectory", schema=None) as batch_op:
        batch_op.drop_index("idx_growth_trajectory_user_id_occurred_at")
    op.drop_table("t_growth_trajectory")

    op.drop_table("t_action_weight")
    op.drop_table("t_action_streak")

    with op.batch_alter_table("t_action_checkin", schema=None) as batch_op:
        batch_op.drop_index("idx_action_checkin_user_id_completed_at")
        batch_op.drop_index("idx_action_checkin_action_id")
    op.drop_table("t_action_checkin")

    with op.batch_alter_table("t_action", schema=None) as batch_op:
        batch_op.drop_index("idx_action_user_id_status")
        batch_op.drop_index("idx_action_user_id_due_date")
    op.drop_table("t_action")
