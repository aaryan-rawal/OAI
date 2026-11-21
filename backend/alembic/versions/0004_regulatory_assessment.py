"""Store server-generated, source-referenced regulatory assessments on cargo."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_regulatory_assessment"
down_revision = "0003_cargo_handling_times"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("manual_cargo", sa.Column("compliance_assessment", postgresql.JSONB(), nullable=True))

def downgrade():
    op.drop_column("manual_cargo", "compliance_assessment")
