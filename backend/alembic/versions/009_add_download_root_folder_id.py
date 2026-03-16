"""Add root_folder_id to downloads table.

Revision ID: 009
Revises: 008
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "downloads",
        sa.Column("root_folder_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_downloads_root_folder_id",
        "downloads",
        "root_folders",
        ["root_folder_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_downloads_root_folder_id", "downloads", ["root_folder_id"])


def downgrade() -> None:
    op.drop_index("ix_downloads_root_folder_id", table_name="downloads")
    op.drop_constraint("fk_downloads_root_folder_id", "downloads", type_="foreignkey")
    op.drop_column("downloads", "root_folder_id")
