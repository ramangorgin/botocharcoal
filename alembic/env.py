"""Alembic environment configuration for Botocharcoal."""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text
from alembic import context

from app.db.base import Base
from app.db.models import *



# Alembic Config object
config = context.config

# Override sqlalchemy.url from environment variable if set
db_url = os.environ.get("DATABASE_URL")
if db_url:
    # Use sync driver for Alembic (psycopg2) instead of async (asyncpg)
    sync_url = db_url.replace("+asyncpg", "")
    config.set_main_option("sqlalchemy.url", sync_url)
# else use the URL from alembic.ini (must use sync driver)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
