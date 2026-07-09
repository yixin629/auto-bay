"""add social automation tables

Revision ID: a44ce4fb8d0a
Revises: f08f6a1c4e8d
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a44ce4fb8d0a"
down_revision: Union[str, None] = "f08f6a1c4e8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "social_automations",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("publisher_type", sa.String(length=50), nullable=False, server_default="webhook_bridge"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("schedule_minutes", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=20), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("content_template", sa.Text(), nullable=True),
        sa.Column("content_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("publisher_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["platform_connection_id"], ["platform_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_social_automations_user_id", "social_automations", ["user_id"])
    op.create_index("ix_social_automations_platform_connection_id", "social_automations", ["platform_connection_id"])
    op.create_index("ix_social_automations_campaign_id", "social_automations", ["campaign_id"])
    op.create_index("ix_social_automations_platform", "social_automations", ["platform"])
    op.create_index("ix_social_automations_next_run_at", "social_automations", ["next_run_at"])

    op.create_table(
        "social_post_logs",
        sa.Column("automation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["automation_id"], ["social_automations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_social_post_logs_automation_id", "social_post_logs", ["automation_id"])
    op.create_index("ix_social_post_logs_user_id", "social_post_logs", ["user_id"])
    op.create_index("ix_social_post_logs_platform", "social_post_logs", ["platform"])
    op.create_index("ix_social_post_logs_status", "social_post_logs", ["status"])
    op.create_index("ix_social_post_logs_posted_at", "social_post_logs", ["posted_at"])


def downgrade() -> None:
    op.drop_index("ix_social_post_logs_posted_at", table_name="social_post_logs")
    op.drop_index("ix_social_post_logs_status", table_name="social_post_logs")
    op.drop_index("ix_social_post_logs_platform", table_name="social_post_logs")
    op.drop_index("ix_social_post_logs_user_id", table_name="social_post_logs")
    op.drop_index("ix_social_post_logs_automation_id", table_name="social_post_logs")
    op.drop_table("social_post_logs")

    op.drop_index("ix_social_automations_next_run_at", table_name="social_automations")
    op.drop_index("ix_social_automations_platform", table_name="social_automations")
    op.drop_index("ix_social_automations_campaign_id", table_name="social_automations")
    op.drop_index("ix_social_automations_platform_connection_id", table_name="social_automations")
    op.drop_index("ix_social_automations_user_id", table_name="social_automations")
    op.drop_table("social_automations")
