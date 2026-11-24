"""create approval_requests

Revision ID: 1f6a8bbc26af
Revises: cb98a5602890
Create Date: 2026-11-21 13:38:14.522807

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1f6a8bbc26af'
down_revision: Union[str, Sequence[str], None] = 'cb98a5602890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("thread_id", sa.String(100), nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=False),
        # JSONB stores what the human must review (tool name and arguments)
        sa.Column("payload", postgresql.JSONB, nullable=False),
        # pending -> approved or rejected
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("approval_requests")
