"""Require phone verification during registration and support OTP challenges."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0007_registration_phone_otp"
down_revision = "0006_hazardous_cargo"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("app_users", sa.Column("phone", sa.String(length=24), nullable=True))
    op.add_column("app_users", sa.Column("phone_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_app_users_phone", "app_users", ["phone"], unique=True)
    op.create_table("registration_otps",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("phone", sa.String(length=24), nullable=False),
        sa.Column("otp_hash", sa.String(length=128), nullable=False),
        sa.Column("registration_payload", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_registration_otps_phone", "registration_otps", ["phone"])

def downgrade():
    op.drop_index("ix_registration_otps_phone", table_name="registration_otps")
    op.drop_table("registration_otps")
    op.drop_index("ix_app_users_phone", table_name="app_users")
    op.drop_column("app_users", "phone_verified")
    op.drop_column("app_users", "phone")
