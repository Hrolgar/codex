"""Add catalog_status column to authors table.

Revision ID: 003
Revises: 002
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("authors", sa.Column("catalog_status", sa.String(20), server_default="idle", nullable=False))


def downgrade() -> None:
    op.drop_column("authors", "catalog_status")
