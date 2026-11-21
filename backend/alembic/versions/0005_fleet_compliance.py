"""Add fleet compliance metadata and driver rest-event ledger.

Non-destructive: adds nullable/defaulted columns and one new table only.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_fleet_compliance"
down_revision = "0004_regulatory_assessment"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("fleet_drivers", sa.Column("license_number", sa.String(40), nullable=True))
    op.add_column("fleet_drivers", sa.Column("aadhaar_last4", sa.String(4), nullable=True))
    op.add_column("fleet_drivers", sa.Column("pan_masked", sa.String(16), nullable=True))
    op.add_column("fleet_drivers", sa.Column("date_of_birth", sa.String(20), nullable=True))
    op.add_column("fleet_drivers", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("fleet_drivers", sa.Column("verification_status", sa.String(30), server_default="not_submitted", nullable=False))
    op.add_column("fleet_drivers", sa.Column("verification_result", postgresql.JSONB(), nullable=True))
    op.add_column("fleet_drivers", sa.Column("blacklisted", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("fleet_drivers", sa.Column("blacklist_reason", sa.Text(), nullable=True))
    op.add_column("fleet_containers", sa.Column("documents", postgresql.JSONB(), server_default="{}", nullable=False))
    op.create_table("driver_rest_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("fleet_drivers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rest_type", sa.String(30), nullable=False, server_default="rest"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_driver_rest_events_driver_id", "driver_rest_events", ["driver_id"])

def downgrade():
    op.drop_index("ix_driver_rest_events_driver_id", table_name="driver_rest_events")
    op.drop_table("driver_rest_events")
    op.drop_column("fleet_containers", "documents")
    for col in ["blacklist_reason", "blacklisted", "verification_result", "verification_status", "address", "date_of_birth", "pan_masked", "aadhaar_last4", "license_number"]:
        op.drop_column("fleet_drivers", col)
