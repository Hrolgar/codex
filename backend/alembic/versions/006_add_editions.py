"""Add editions table.

Revision ID: 006
Revises: 005
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "editions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("language", sa.String(10)),
        sa.Column("format", sa.String(20)),
        sa.Column("media_type", sa.String(20)),
        sa.Column("isbn_10", sa.String(13)),
        sa.Column("isbn_13", sa.String(17)),
        sa.Column("asin", sa.String(20)),
        sa.Column("publisher", sa.String(300)),
        sa.Column("publish_year", sa.Integer),
        sa.Column("page_count", sa.Integer),
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("cover_url", sa.String(1000)),
        sa.Column("description", sa.String),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_editions_book_id", "editions", ["book_id"])
    op.create_index("ix_editions_language", "editions", ["language"])


def downgrade() -> None:
    op.drop_index("ix_editions_language", table_name="editions")
    op.drop_index("ix_editions_book_id", table_name="editions")
    op.drop_table("editions")
