"""store user profile as jsonb instead of a yaml-text column

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-28

"""

import json

import sqlalchemy as sa
import yaml
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile", sa.JSON(), nullable=True))

    # Backfill: parse each row's existing YAML text (already produced by
    # yaml.safe_dump(profile_to_dict(...))) back into a plain dict, so a row
    # written under the old TEXT column keeps its data under the new one.
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, profile_yaml FROM users")).fetchall()
    for row_id, profile_yaml in rows:
        parsed = yaml.safe_load(profile_yaml) if profile_yaml else None
        conn.execute(
            sa.text("UPDATE users SET profile = CAST(:profile AS JSON) WHERE id = :id"),
            {"profile": json.dumps(parsed) if parsed else None, "id": row_id},
        )

    op.drop_column("users", "profile_yaml")


def downgrade() -> None:
    op.add_column("users", sa.Column("profile_yaml", sa.String(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, profile FROM users")).fetchall()
    for row_id, profile in rows:
        text = yaml.safe_dump(profile, sort_keys=False, allow_unicode=True) if profile else None
        conn.execute(
            sa.text("UPDATE users SET profile_yaml = CAST(:profile_yaml AS VARCHAR) WHERE id = :id"),
            {"profile_yaml": text, "id": row_id},
        )

    op.drop_column("users", "profile")
