"""add password_hash to customers

Revision ID: 04d9cb571074
Revises: 1f6a8bbc26af
Create Date: 2026-11-21 20:08:35.525190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04d9cb571074'
down_revision: Union[str, Sequence[str], None] = '1f6a8bbc26af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable, because the existing customers have no password yet
    op.add_column(
        "customers", sa.Column("password_hash", sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("customers", "password_hash")
