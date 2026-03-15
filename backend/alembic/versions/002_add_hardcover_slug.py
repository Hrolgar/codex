"""Add hardcover_slug column to books table.

Revision ID: 002_hardcover_slug
Revises: 001_unique_names
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from alembic import op

revision = "002_hardcover_slug"
down_revision = "001_unique_names"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("books", sa.Column("hardcover_slug", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("books", "hardcover_slug")
