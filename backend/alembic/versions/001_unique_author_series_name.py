"""Add unique constraints on author and series name.

Revision ID: 001_unique_names
Revises:
Create Date: 2026-03-15
"""

from alembic import op

revision = "001_unique_names"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_authors_name", "authors", ["name"])
    op.create_unique_constraint("uq_series_name", "series", ["name"])


def downgrade() -> None:
    op.drop_constraint("uq_series_name", "series", type_="unique")
    op.drop_constraint("uq_authors_name", "authors", type_="unique")
