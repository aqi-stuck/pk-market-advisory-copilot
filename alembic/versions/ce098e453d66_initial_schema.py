from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "ce098e453d66"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("lane", sa.String(length=50), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
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
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=True),
        sa.Column("qdrant_point_id", sa.String(length=100), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
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
        sa.Column("lane", sa.String(length=50), nullable=False),
        sa.Column(
            "status", sa.String(length=30), server_default="pending", nullable=False
        ),
        sa.Column("source_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ingestion_runs_lane"), "ingestion_runs", ["lane"], unique=False
    )

    op.create_table(
        "query_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("lane_hint", sa.String(), nullable=True),
        sa.Column("retrieval_k", sa.Integer(), nullable=True),
        sa.Column("reranked_k", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
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
