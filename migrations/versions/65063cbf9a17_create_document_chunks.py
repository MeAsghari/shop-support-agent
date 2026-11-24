"""create document_chunks

Revision ID: 65063cbf9a17
Revises: fb9fc5b50a35
Create Date: 2026-11-15 10:40:12.195804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65063cbf9a17'
down_revision: Union[str, Sequence[str], None] = 'fb9fc5b50a35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make sure the pgvector extension is on (safe to run again)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create the table. vector(1024) must match the embedding model size
    op.execute(
        """
        CREATE TABLE document_chunks (
            id SERIAL PRIMARY KEY,
            source VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1024) NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
