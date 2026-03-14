"""Add author catalog columns and book monitored flag.

Revision ID: 002
Revises: 001
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("authors", sa.Column("monitored", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("authors", sa.Column("openlibrary_key", sa.String(50), nullable=True))
    op.add_column("authors", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("authors", sa.Column("photo_url", sa.String(1000), nullable=True))
    op.add_column("books", sa.Column("monitored", sa.Boolean(), server_default="false", nullable=False))


def downgrade() -> None:
    op.drop_column("books", "monitored")
    op.drop_column("authors", "photo_url")
    op.drop_column("authors", "bio")
    op.drop_column("authors", "openlibrary_key")
    op.drop_column("authors", "monitored")
