"""Add revocable mobile sessions without modifying existing users or operations.

Revision ID: e81501c7a001
Revises: d457194c1424
"""

import sqlalchemy as sa
from alembic import op

revision = "e81501c7a001"
down_revision = "d457194c1424"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mobile_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("auth_version", sa.Integer(), nullable=False),
        sa.Column("device_name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("expires_at > created_at", name="positive_lifetime"),
    )
    op.create_index("ix_mobile_sessions_user_id", "mobile_sessions", ["user_id"])
    op.create_index("ix_mobile_sessions_expires_at", "mobile_sessions", ["expires_at"])


def downgrade():
    op.drop_table("mobile_sessions")
