"""create orders and order_items

Revision ID: fb9fc5b50a35
Revises: 5bce9e507fbf
Create Date: 2026-11-14 10:37:49.188776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb9fc5b50a35'
down_revision: Union[str, Sequence[str], None] = '5bce9e507fbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the orders table (each order belongs to one customer)
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "customer_id",
            sa.Integer,
            sa.ForeignKey("customers.id"),  # points to customers.id
            nullable=False,
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Create the order_items table (each row is one product inside one order)
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "order_id",
            sa.Integer,
            sa.ForeignKey("orders.id"),  # points to orders.id
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer,
            sa.ForeignKey("products.id"),  # points to products.id
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer, nullable=False),
        # Save the price at purchase time, because product prices can change later
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
    )


def downgrade() -> None:
    # Drop order_items first, because it depends on orders
    op.drop_table("order_items")
    op.drop_table("orders")
