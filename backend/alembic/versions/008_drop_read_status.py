"""Drop read_status and date_read columns from books table.

Revision ID: 008
Revises: 007
Create Date: 2026-03-15
"""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("books", "date_read")
    op.drop_column("books", "read_status")


def downgrade() -> None:
    import sqlalchemy as sa

    op.add_column("books", sa.Column("read_status", sa.String(20), server_default="unread", nullable=False))
    op.add_column("books", sa.Column("date_read", sa.DateTime(timezone=True), nullable=True))
