import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Allow overriding sqlalchemy.url via environment variable
env_url = os.getenv("ALEMBIC_DATABASE_URL") or os.getenv("DATABASE_URL")
if env_url:
    # Escape '%' for ConfigParser interpolation
    config.set_main_option("sqlalchemy.url", env_url.replace('%', '%%'))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from db.models import Base
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # Optional SSL for RDS when ALEMBIC_SSL=1
    require_ssl = os.getenv("ALEMBIC_SSL", "0") == "1"
    connect_args = {"ssl": True} if require_ssl else {}

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    use_sync = os.getenv("ALEMBIC_USE_SYNC", "0") == "1"
    if use_sync:
        # Synchronous engine using psycopg2
        section = config.get_section(config.config_ini_section, {})
        url = section.get("sqlalchemy.url")
        # For psycopg2, respect ALEMBIC_SSL with sslmode=require if not in URL
        require_ssl = os.getenv("ALEMBIC_SSL", "0") == "1"
        connect_args = {"sslmode": "require"} if (require_ssl and (url and "sslmode=" not in url)) else {}
        engine = create_engine(url, poolclass=pool.NullPool, connect_args=connect_args, future=True)
        with engine.connect() as connection:
            do_run_migrations(connection)
        engine.dispose()
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
