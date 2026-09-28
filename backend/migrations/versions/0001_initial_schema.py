"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-28

"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asyncapply_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_extract_jd", sa.String(), nullable=False),
        sa.Column("model_evaluate_job", sa.String(), nullable=False),
        sa.Column("model_find_contact", sa.String(), nullable=False),
        sa.Column("parallelism", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("stage_timeout", sa.Integer(), nullable=False),
        sa.Column("fetch_timeout", sa.Integer(), nullable=False),
        sa.Column("cv_max_pages", sa.Integer(), nullable=False),
        sa.Column("output_dir", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "asyncapply_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "asyncapply_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("raw_input", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("company_type", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("verdict", sa.String(), nullable=True),
        sa.Column("strengths", sa.JSON(), nullable=True),
        sa.Column("gaps", sa.JSON(), nullable=True),
        sa.Column("legitimacy", sa.String(), nullable=True),
        sa.Column("work_auth_tier", sa.String(), nullable=True),
        sa.Column("min_years_required", sa.Integer(), nullable=True),
        sa.Column("hard_stop_reason", sa.String(), nullable=True),
        sa.Column("cv_pdf_path", sa.String(), nullable=True),
        sa.Column("cover_letter_pdf_path", sa.String(), nullable=True),
        sa.Column("contact_name", sa.String(), nullable=True),
        sa.Column("contact_message", sa.String(), nullable=True),
        sa.Column("contacts", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["asyncapply_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("asyncapply_items")
    op.drop_table("asyncapply_batches")
    op.drop_table("asyncapply_settings")
