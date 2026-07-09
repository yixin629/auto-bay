"""add cn platforms

Revision ID: 9f92a56a4101
Revises: 156bc3da2c48
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f92a56a4101"
down_revision: Union[str, None] = "156bc3da2c48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLAlchemy Enum(Platform) is stored by enum member names (uppercase).
    op.execute("ALTER TYPE platform ADD VALUE IF NOT EXISTS 'DOUYIN'")
    op.execute("ALTER TYPE platform ADD VALUE IF NOT EXISTS 'XIAOHONGSHU'")


def downgrade() -> None:
    # Postgres enum value removal is non-trivial and intentionally omitted.
    pass
