"""Idempotent assistant catalog actions; preserve all existing records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f72101c7a002"
down_revision = "e81501c7a001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mobile_actions",
        sa.Column("key", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mobile_actions_user_id", "mobile_actions", ["user_id"])


def downgrade():
    op.drop_table("mobile_actions")
