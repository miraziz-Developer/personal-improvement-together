import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from pit.infrastructure.schema import metadata
from pit.shared.infrastructure.db import create_engine

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)


def database_url() -> str:
    explicit = config.get_main_option("sqlalchemy.url") or os.environ.get("PIT_DATABASE_URL")
    if explicit:
        return explicit
    from pit.config import get_settings  # reads backend/.env

    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_engine(database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
