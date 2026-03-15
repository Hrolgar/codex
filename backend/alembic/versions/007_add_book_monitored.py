"""Change book monitored default to true.

Revision ID: 007
Revises: 006
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "books",
        "monitored",
        server_default="true",
    )


def downgrade() -> None:
    op.alter_column(
        "books",
        "monitored",
        server_default="false",
    )
