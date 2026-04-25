"""initial schema

Revision ID: ce098e453d66
Revises:
Create Date: 2026-04-24 11:54:52.966462

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ce098e453d66"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tables first
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=True),
        sa.Column("lane", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_lane"), "documents", ["lane"], unique=False)
    op.create_index(
        op.f("ix_documents_source_name"), "documents", ["source_name"], unique=False
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lane", sa.String(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ingestion_runs_lane"), "ingestion_runs", ["lane"], unique=False
    )

    op.create_table(
        "query_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("query_logs")
    op.drop_index(op.f("ix_ingestion_runs_lane"), table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
    op.drop_table("chunks")
    op.drop_index(op.f("ix_documents_source_name"), table_name="documents")
    op.drop_index(op.f("ix_documents_lane"), table_name="documents")
    op.drop_table("documents")
