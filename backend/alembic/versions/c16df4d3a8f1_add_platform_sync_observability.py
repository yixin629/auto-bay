"""add platform sync observability

Revision ID: c16df4d3a8f1
Revises: 9f92a56a4101
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c16df4d3a8f1"
down_revision: Union[str, None] = "9f92a56a4101"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_connections",
        sa.Column("last_sync_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "platform_connections",
        sa.Column("last_sync_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_connections", "last_sync_error")
    op.drop_column("platform_connections", "last_sync_count")
