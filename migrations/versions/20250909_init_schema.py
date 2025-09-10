"""init schema

Revision ID: 20250909_init_schema
Revises: 
Create Date: 2025-09-09 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250909_init_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sites
    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("tz", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create devices
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create points
    op.create_table(
        "points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("point_name", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("site_id", "point_name", name="uq_points_site_name"),
    )

    # Create point_metadata_history
    op.create_table(
        "point_metadata_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("point_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("points.id", ondelete="CASCADE"), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False),
        sa.Column("meta_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("point_id", "effective_from", name="uq_point_meta_version"),
    )

    # Create measurements
    op.create_table(
        "measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("point_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("points.id", ondelete="CASCADE"), nullable=False),
        sa.Column("measurement_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("point_name", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text()),
        sa.Column("value", sa.Numeric(14, 6), nullable=False),
        sa.Column("quality", sa.Integer()),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("meta_hash", sa.Text()),
        sa.UniqueConstraint("point_id", "measurement_timestamp", name="uq_point_measurement_time"),
    )

    # Create device_state
    op.create_table(
        "device_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("last_seen_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_upload_ts", sa.DateTime(timezone=True)),
        sa.Column("queue_depth", sa.Integer()),
        sa.Column("agent_version", sa.Text()),
        sa.Column("poll_interval_s", sa.Integer()),
        sa.Column("cpu_pct", sa.Numeric(5, 2)),
        sa.Column("disk_free_gb", sa.Numeric(10, 2)),
        sa.Column("status", sa.Enum("READY", "DEGRADED", "ERROR", name="device_status"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("device_state")
    op.drop_table("measurements")
    op.drop_table("point_metadata_history")
    op.drop_table("points")
    op.drop_table("devices")
    op.drop_table("sites")
    op.execute("DROP TYPE IF EXISTS device_status")
