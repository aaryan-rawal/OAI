"""Add operational application tables without altering legacy tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_operational_app"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("app_users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False), sa.Column("name", sa.String(160), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False), sa.Column("role", sa.String(40), nullable=False, server_default="client"),
        sa.Column("tier", sa.String(30), nullable=False, server_default="basic"),
        sa.Column("organization_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("organization_name", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_app_users_email"))
    op.create_index("ix_app_users_email", "app_users", ["email"], unique=True)
    op.create_table("manual_cargo",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("category", sa.String(80), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=True), sa.Column("rate_inr", sa.Float(), nullable=True),
        sa.Column("pickup", postgresql.JSONB(), nullable=False), sa.Column("drop", postgresql.JSONB(), nullable=False),
        sa.Column("pickup_window_start", sa.String(40), nullable=True), sa.Column("pickup_window_end", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="manual"))
    op.create_index("ix_manual_cargo_owner_id", "manual_cargo", ["owner_id"])
    op.create_table("match_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("route_id", sa.String(80), nullable=False), sa.Column("route_version", sa.Integer(), nullable=False),
        sa.Column("off_route_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("response", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_match_runs_user_id", "match_runs", ["user_id"])
    op.create_table("shipments",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(80), nullable=False), sa.Column("candidate_id", sa.String(100), nullable=False),
        sa.Column("route_id", sa.String(80), nullable=False), sa.Column("route_version", sa.Integer(), nullable=False),
        sa.Column("route_name", sa.String(160), nullable=False), sa.Column("origin", postgresql.JSONB(), nullable=False),
        sa.Column("destination", postgresql.JSONB(), nullable=False), sa.Column("route_polyline", postgresql.JSONB(), nullable=False),
        sa.Column("candidate", postgresql.JSONB(), nullable=False), sa.Column("status", sa.String(40), nullable=False),
        sa.Column("status_history", postgresql.JSONB(), nullable=False), sa.Column("assigned_driver_id", sa.String(100), nullable=True),
        sa.Column("fleet_container_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_shipments_user_id", "shipments", ["user_id"])
    op.create_table("fleet_drivers",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True), sa.Column("organization_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(160), nullable=False), sa.Column("email", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "email", name="uq_driver_org_email"))
    op.create_index("ix_fleet_drivers_organization_id", "fleet_drivers", ["organization_id"])
    op.create_table("fleet_containers",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True), sa.Column("organization_id", sa.String(100), nullable=False),
        sa.Column("registration_number", sa.String(40), nullable=False), sa.Column("truck", postgresql.JSONB(), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("fleet_drivers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "registration_number", name="uq_container_org_registration"))
    op.create_index("ix_fleet_containers_organization_id", "fleet_containers", ["organization_id"])


def downgrade():
    op.drop_index("ix_fleet_containers_organization_id", table_name="fleet_containers")
    op.drop_table("fleet_containers")
    op.drop_index("ix_fleet_drivers_organization_id", table_name="fleet_drivers")
    op.drop_table("fleet_drivers")
    op.drop_index("ix_shipments_user_id", table_name="shipments")
    op.drop_table("shipments")
    op.drop_index("ix_match_runs_user_id", table_name="match_runs")
    op.drop_table("match_runs")
    op.drop_index("ix_manual_cargo_owner_id", table_name="manual_cargo")
    op.drop_table("manual_cargo")
    op.drop_index("ix_app_users_email", table_name="app_users")
    op.drop_table("app_users")
