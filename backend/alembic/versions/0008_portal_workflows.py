"""Add organizations, in-portal notifications, cargo requests and audit trail."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0008_portal_workflows"
down_revision = "0007_registration_phone_otp"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("organizations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_owner_approval"),
        sa.Column("profile", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_organizations_name", "organizations", ["name"])
    op.create_index("ix_organizations_owner_user_id", "organizations", ["owner_user_id"])
    op.create_table("in_portal_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=False)), sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("read_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_in_portal_notifications_recipient_user_id", "in_portal_notifications", ["recipient_user_id"])
    op.create_index("ix_in_portal_notifications_organization_id", "in_portal_notifications", ["organization_id"])
    op.create_index("ix_in_portal_notifications_created_at", "in_portal_notifications", ["created_at"])
    op.create_table("driver_cargo_requests",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("driver_user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cargo_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("manual_cargo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"), sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("review_note", sa.Text()),
        sa.UniqueConstraint("driver_user_id", "cargo_id", name="uq_driver_cargo_request"))
    op.create_index("ix_driver_cargo_requests_organization_id", "driver_cargo_requests", ["organization_id"])
    op.create_index("ix_driver_cargo_requests_driver_user_id", "driver_cargo_requests", ["driver_user_id"])
    op.create_index("ix_driver_cargo_requests_cargo_id", "driver_cargo_requests", ["cargo_id"])
    op.create_table("platform_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="SET NULL")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=False)), sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False), sa.Column("entity_id", sa.String(80), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_platform_audit_logs_actor_user_id", "platform_audit_logs", ["actor_user_id"])
    op.create_index("ix_platform_audit_logs_organization_id", "platform_audit_logs", ["organization_id"])
    op.create_index("ix_platform_audit_logs_created_at", "platform_audit_logs", ["created_at"])

def downgrade():
    for t, i in [("platform_audit_logs","ix_platform_audit_logs_created_at"),("platform_audit_logs","ix_platform_audit_logs_organization_id"),("platform_audit_logs","ix_platform_audit_logs_actor_user_id"),("driver_cargo_requests","ix_driver_cargo_requests_cargo_id"),("driver_cargo_requests","ix_driver_cargo_requests_driver_user_id"),("driver_cargo_requests","ix_driver_cargo_requests_organization_id"),("in_portal_notifications","ix_in_portal_notifications_created_at"),("in_portal_notifications","ix_in_portal_notifications_organization_id"),("in_portal_notifications","ix_in_portal_notifications_recipient_user_id"),("organizations","ix_organizations_owner_user_id"),("organizations","ix_organizations_name")]: op.drop_index(i, table_name=t)
    for t in ["platform_audit_logs","driver_cargo_requests","in_portal_notifications","organizations"]: op.drop_table(t)
