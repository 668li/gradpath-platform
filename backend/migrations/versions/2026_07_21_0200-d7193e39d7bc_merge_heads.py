"""merge heads

Revision ID: d7193e39d7bc
Revises: bbcc8a2def16, add_notification_archive
Create Date: 2026-07-21 02:00:51.618742+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7193e39d7bc'
down_revision: Union[str, None] = ('bbcc8a2def16', 'add_notification_archive')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
