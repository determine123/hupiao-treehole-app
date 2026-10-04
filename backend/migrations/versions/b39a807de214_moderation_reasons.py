"""Separate author-facing moderation reasons from internal audit notes."""

from alembic import op
import sqlalchemy as sa

revision = "b39a807de214"
down_revision = "47350762dcb6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "audit",
        sa.Column(
            "target_type", sa.String(16), nullable=False, server_default="unknown"
        ),
    )
    op.add_column(
        "audit",
        sa.Column("public_reason", sa.String(300), nullable=False, server_default=""),
    )
    op.create_index("audit_feed", "audit", ["created", "id"])
    op.create_index(
        "audit_target_feed", "audit", ["target", "target_type", "created", "id"]
    )


def downgrade():
    op.drop_index("audit_target_feed", table_name="audit")
    op.drop_index("audit_feed", table_name="audit")
    op.drop_column("audit", "public_reason")
    op.drop_column("audit", "target_type")
