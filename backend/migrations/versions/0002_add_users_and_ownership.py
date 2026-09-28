"""add users table and batch ownership

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("firebase_uid", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column("profile_yaml", sa.String(), nullable=True),
        sa.Column("agent_dna_md", sa.String(), nullable=True),
        sa.Column("token_budget_usd", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("spent_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("school", sa.String(), nullable=True),
        sa.Column("grad_year", sa.Integer(), nullable=True),
        sa.Column("field_of_study", sa.String(), nullable=True),
        sa.Column("target_roles", sa.String(), nullable=True),
        sa.Column("referral_source", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("firebase_uid"),
    )

    # Not-null straight away: this migration ships before any real deploy has
    # data, so there is nothing to backfill.
    op.add_column("asyncapply_batches", sa.Column("user_id", sa.Integer(), nullable=False))
    op.create_foreign_key(
        "fk_asyncapply_batches_user_id", "asyncapply_batches", "users", ["user_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_asyncapply_batches_user_id", "asyncapply_batches", type_="foreignkey")
    op.drop_column("asyncapply_batches", "user_id")
    op.drop_table("users")
