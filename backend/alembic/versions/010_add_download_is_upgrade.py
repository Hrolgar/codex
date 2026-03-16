"""Add is_upgrade flag to downloads table.

Revision ID: 010
Revises: 009
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "downloads",
        sa.Column("is_upgrade", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("downloads", "is_upgrade")
