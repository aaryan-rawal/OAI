"""Add explicit handling/waiting duration inputs for fail-closed active-time checks."""
from alembic import op
import sqlalchemy as sa

revision = "0003_cargo_handling_times"
down_revision = "0002_operational_app"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("manual_cargo", sa.Column("loading_minutes", sa.Float(), nullable=True))
    op.add_column("manual_cargo", sa.Column("unloading_minutes", sa.Float(), nullable=True))
    op.add_column("manual_cargo", sa.Column("waiting_minutes", sa.Float(), nullable=True))

def downgrade():
    op.drop_column("manual_cargo", "waiting_minutes")
    op.drop_column("manual_cargo", "unloading_minutes")
    op.drop_column("manual_cargo", "loading_minutes")
