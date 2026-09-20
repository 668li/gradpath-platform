"""add explicit evidence provider verification fields

Revision ID: 20260920evidence
Revises: 20260920_decision_lifecycle
"""
from alembic import op
import sqlalchemy as sa

revision = "20260920evidence"
down_revision = "20260920_decision_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("decision_evidence", sa.Column("provider_name", sa.String(length=50), nullable=True))
    op.add_column("decision_evidence", sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="internal_unverified"))
    op.add_column("decision_evidence", sa.Column("verification_source_url", sa.String(length=2000), nullable=True))
    op.add_column("decision_evidence", sa.Column("verified_on", sa.Date(), nullable=True))
    op.create_index("ix_decision_evidence_provider_name", "decision_evidence", ["provider_name"])
    op.create_index("ix_decision_evidence_verification_status", "decision_evidence", ["verification_status"])


def downgrade() -> None:
    op.drop_index("ix_decision_evidence_verification_status", table_name="decision_evidence")
    op.drop_index("ix_decision_evidence_provider_name", table_name="decision_evidence")
    op.drop_column("decision_evidence", "verified_on")
    op.drop_column("decision_evidence", "verification_source_url")
    op.drop_column("decision_evidence", "verification_status")
    op.drop_column("decision_evidence", "provider_name")
