"""add agent dna choices and admin note columns

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("agent_dna_choices", sa.JSON(), nullable=True))
    op.add_column("asyncapply_settings", sa.Column("agent_dna_admin_note", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("asyncapply_settings", "agent_dna_admin_note")
    op.drop_column("users", "agent_dna_choices")
