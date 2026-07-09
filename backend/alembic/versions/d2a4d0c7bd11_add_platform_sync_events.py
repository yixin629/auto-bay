"""add platform sync events

Revision ID: d2a4d0c7bd11
Revises: c16df4d3a8f1
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d2a4d0c7bd11"
down_revision: Union[str, None] = "c16df4d3a8f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    platform_enum = postgresql.ENUM(
        "EBAY",
        "AMAZON",
        "SHOPIFY",
        "TIKTOK",
        "DOUYIN",
        "XIAOHONGSHU",
        "HARVEY_NORMAN",
        name="platform",
        create_type=False,
    )

    op.create_table(
        "platform_sync_events",
        sa.Column("platform_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", platform_enum, nullable=False),
        sa.Column("region", sa.String(length=5), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["platform_connection_id"], ["platform_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_sync_events_platform_connection_id", "platform_sync_events", ["platform_connection_id"])
    op.create_index("ix_platform_sync_events_user_id", "platform_sync_events", ["user_id"])
    op.create_index("ix_platform_sync_events_event_type", "platform_sync_events", ["event_type"])
    op.create_index("ix_platform_sync_events_status", "platform_sync_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_platform_sync_events_status", table_name="platform_sync_events")
    op.drop_index("ix_platform_sync_events_event_type", table_name="platform_sync_events")
    op.drop_index("ix_platform_sync_events_user_id", table_name="platform_sync_events")
    op.drop_index("ix_platform_sync_events_platform_connection_id", table_name="platform_sync_events")
    op.drop_table("platform_sync_events")
