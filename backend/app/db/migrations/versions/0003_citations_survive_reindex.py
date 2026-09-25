"""Citações sobrevivem à reindexação; resposta sem citação; início das referências (plano v11, seções 4, 5.3, 5.6 e 6.4).

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("citations_chunk_id_fkey", "citations", type_="foreignkey")
    op.alter_column("citations", "chunk_id", nullable=True)
    op.create_foreign_key("citations_chunk_id_fkey", "citations", "chunks", ["chunk_id"], ["id"], ondelete="SET NULL")
    op.add_column("messages", sa.Column("uncited", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("documents", sa.Column("references_start_page", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "references_start_page")
    op.drop_column("messages", "uncited")
    op.drop_constraint("citations_chunk_id_fkey", "citations", type_="foreignkey")
    # Citações que perderam o trecho não cabem no esquema antigo.
    op.execute("DELETE FROM citations WHERE chunk_id IS NULL")
    op.alter_column("citations", "chunk_id", nullable=False)
    op.create_foreign_key("citations_chunk_id_fkey", "citations", "chunks", ["chunk_id"], ["id"])
