import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from db import Base


def get_database_url() -> str:
    host = os.getenv("POSTGRES_HOST", "db")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    database = os.getenv("POSTGRES_DB", "hvac")

    return URL.create(
        drivername="postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
    )


def main() -> None:
    url = get_database_url()
    engine = create_engine(url, future=True)
    allow_destructive = os.getenv("ALLOW_DESTRUCTIVE_INIT", "0") == "1"
    compress_after_days = int(os.getenv("COMPRESS_AFTER_DAYS", "7"))
    retain_days = int(os.getenv("RETAIN_DAYS", "365"))
    desired_time_col = "measurement_timestamp"
    desired_space_col = "point_id"
    desired_num_partitions = 8
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        # Optionally drop unmanaged legacy tables
        if allow_destructive:
            conn.execute(text("DROP TABLE IF EXISTS validation_rules CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS write_commands CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS command_ack CASCADE;"))

        # Check existing hypertable dimensions to decide if we need to recreate
        dims = conn.execute(
            text(
                "SELECT dimension_type, column_name, COALESCE(num_partitions, 0) AS num_partitions "
                "FROM timescaledb_information.dimensions WHERE hypertable_name='measurements'"
            )
        ).fetchall()

        need_recreate = False
        if dims:
            time_dims = [d for d in dims if d[0] == "Time"]
            space_dims = [d for d in dims if d[0] == "Space"]
            if not time_dims or time_dims[0][1] != desired_time_col:
                need_recreate = True
            if not space_dims or space_dims[0][1] != desired_space_col or int(space_dims[0][2]) != desired_num_partitions:
                need_recreate = True

        if need_recreate and allow_destructive:
            conn.execute(text("DROP TABLE IF EXISTS measurements CASCADE;"))
            conn.commit()

        # Create all tables according to ORM models and commit so DDL is visible
        Base.metadata.create_all(bind=conn)
        conn.commit()

        # Ensure primary key is compatible with hypertable (time + space keys)
        conn.execute(text("ALTER TABLE measurements DROP CONSTRAINT IF EXISTS measurements_pkey;"))
        conn.execute(text("ALTER TABLE measurements ADD PRIMARY KEY (point_id, measurement_timestamp);"))

        # Ensure hypertable with correct time and space dimensions (inline identifiers)
        conn.execute(
            text(
                "SELECT create_hypertable('measurements', 'measurement_timestamp', partitioning_column => 'point_id', number_partitions => 8, if_not_exists => TRUE);"
            )
        )
        conn.execute(
            text(
                "SELECT add_dimension('measurements', 'point_id', number_partitions => 8, if_not_exists => TRUE);"
            )
        )

        # Enable and configure compression
        conn.execute(
            text(
                "ALTER TABLE measurements SET ("
                "timescaledb.compress = true, "
                "timescaledb.compress_orderby = 'measurement_timestamp DESC', "
                "timescaledb.compress_segmentby = 'point_id'"
                ");"
            )
        )
        conn.execute(
            text(
                "SELECT add_compression_policy('measurements', "
                "INTERVAL ':days days', if_not_exists => TRUE);"
            ).bindparams(days=compress_after_days)
        )
        # Retention policy
        conn.execute(
            text(
                "SELECT add_retention_policy('measurements', "
                "INTERVAL ':days days', if_not_exists => TRUE);"
            ).bindparams(days=retain_days)
        )
        conn.commit()
    print("Database initialized; schema synced; 'measurements' uses measurement_timestamp + point_id; compression and retention applied.")


if __name__ == "__main__":
    main()


