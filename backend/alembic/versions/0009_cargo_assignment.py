"""Track exclusive driver assignment for company cargo."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_cargo_assignment"
down_revision = "0008_portal_workflows"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("manual_cargo", sa.Column("assigned_driver_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("app_users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("manual_cargo", sa.Column("assignment_status", sa.String(24), nullable=False, server_default="open"))
    op.create_index("ix_manual_cargo_assigned_driver_id", "manual_cargo", ["assigned_driver_id"])

def downgrade():
    op.drop_index("ix_manual_cargo_assigned_driver_id", table_name="manual_cargo")
    op.drop_column("manual_cargo", "assignment_status")
    op.drop_column("manual_cargo", "assigned_driver_id")
