"""Add hazardous cargo flag and safety evidence metadata."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0006_hazardous_cargo"
down_revision = "0005_fleet_compliance"
branch_labels = None
depends_on = None
def upgrade():
    op.add_column("manual_cargo", sa.Column("hazardous", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("manual_cargo", sa.Column("hazardous_details", postgresql.JSONB(), nullable=True))
def downgrade():
    op.drop_column("manual_cargo", "hazardous_details")
    op.drop_column("manual_cargo", "hazardous")
