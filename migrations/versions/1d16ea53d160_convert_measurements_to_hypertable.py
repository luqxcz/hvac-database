"""convert measurements to hypertable

Revision ID: 1d16ea53d160
Revises: 20250909_init_schema
Create Date: 2025-09-10 14:00:33.782103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d16ea53d160'
down_revision: Union[str, Sequence[str], None] = '20250909_init_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ensure TimescaleDB extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")

    # Drop unique constraint if it duplicates the desired PK
    op.execute(
        "ALTER TABLE measurements DROP CONSTRAINT IF EXISTS uq_point_measurement_time;"
    )

    # Ensure primary key is (point_id, measurement_timestamp)
    op.execute(
        """
        DO $$
        DECLARE
            pk_name text;
            cols text[];
        BEGIN
            SELECT c.conname,
                   array_agg(a.attname ORDER BY k.ordinality)
              INTO pk_name, cols
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.conrelid
              JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ordinality) ON true
              JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
             WHERE t.relname = 'measurements'
               AND c.contype = 'p'
             GROUP BY c.conname;

            IF pk_name IS NULL THEN
                EXECUTE 'ALTER TABLE measurements ADD PRIMARY KEY (point_id, measurement_timestamp)';
            ELSIF cols <> ARRAY['point_id','measurement_timestamp'] THEN
                EXECUTE format('ALTER TABLE measurements DROP CONSTRAINT %I', pk_name);
                EXECUTE 'ALTER TABLE measurements ADD PRIMARY KEY (point_id, measurement_timestamp)';
            END IF;
        END$$;
        """
    )

    # Create hypertable with time + space dimensions
    op.execute(
        "SELECT create_hypertable('measurements', 'measurement_timestamp', partitioning_column => 'point_id', number_partitions => 8, if_not_exists => TRUE);"
    )
    op.execute(
        "SELECT add_dimension('measurements', 'point_id', number_partitions => 8, if_not_exists => TRUE);"
    )

    # Enable and configure compression
    op.execute(
        """
        ALTER TABLE measurements SET (
          timescaledb.compress = true,
          timescaledb.compress_orderby = 'measurement_timestamp DESC',
          timescaledb.compress_segmentby = 'point_id'
        );
        """
    )

    # Add policies (idempotent)
    op.execute(
        "SELECT add_compression_policy('measurements', INTERVAL '7 days', if_not_exists => TRUE);"
    )
    op.execute(
        "SELECT add_retention_policy('measurements', INTERVAL '365 days', if_not_exists => TRUE);"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove policies if present
    op.execute(
        "SELECT remove_compression_policy('measurements');"
    )
    op.execute(
        "SELECT remove_retention_policy('measurements');"
    )

    # Disable table-level compression settings (hypertable remains)
    op.execute(
        "ALTER TABLE measurements SET (timescaledb.compress = false);"
    )
