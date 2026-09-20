"""Decision OS structured lifecycle tables.

Existing DestinationDecision fields remain for backward compatibility.
New writes should use these first-class entities.
"""

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID

revision = "20260920_decision_lifecycle"
down_revision = "20260920_action_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_predictions",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision_id", GUID(), sa.ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric", sa.String(200), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("horizon", sa.Date(), nullable=True),
        sa.Column("success_condition", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_decision_predictions_user_id", "decision_predictions", ["user_id"])
    op.create_index("ix_decision_predictions_decision_id", "decision_predictions", ["decision_id"])
    op.create_index("ix_decision_predictions_status", "decision_predictions", ["status"])

    op.create_table(
        "decision_outcomes",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision_id", GUID(), sa.ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outcome_type", sa.String(30), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_decision_outcomes_user_id", "decision_outcomes", ["user_id"])
    op.create_index("ix_decision_outcomes_decision_id", "decision_outcomes", ["decision_id"])

    op.create_table(
        "decision_reflections",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision_id", GUID(), sa.ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outcome_id", GUID(), sa.ForeignKey("decision_outcomes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("prediction_error", sa.Text(), nullable=True),
        sa.Column("wrong_assumption", sa.Text(), nullable=True),
        sa.Column("omitted_factor", sa.Text(), nullable=True),
        sa.Column("lesson", sa.Text(), nullable=True),
        sa.Column("match_status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_decision_reflections_user_id", "decision_reflections", ["user_id"])
    op.create_index("ix_decision_reflections_decision_id", "decision_reflections", ["decision_id"])


def downgrade() -> None:
    op.drop_table("decision_reflections")
    op.drop_table("decision_outcomes")
    op.drop_table("decision_predictions")
