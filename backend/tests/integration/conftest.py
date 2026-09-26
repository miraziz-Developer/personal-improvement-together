"""Integration tests against a real Postgres (docker compose). Skipped if it is not running."""

import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pit.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from pit.shared.infrastructure.db import create_engine, create_session_factory

TEST_DATABASE_URL = os.environ.get(
    "PIT_TEST_DATABASE_URL", "postgresql+psycopg://pit:pit@localhost:5433/pit_test"
)
TASHKENT_REGION = uuid5(NAMESPACE_URL, "pit:region:tashkent")  # seeded by migration 0002
BACKEND_DIR = Path(__file__).resolve().parents[2]

type UowFactory = Callable[[], SqlAlchemyUnitOfWork]


@pytest.fixture(scope="session")
def migrated_database() -> str:
    try:
        psycopg.connect(TEST_DATABASE_URL.replace("+psycopg", ""), connect_timeout=2).close()
    except psycopg.OperationalError:
        if os.environ.get("PIT_REQUIRE_DB"):  # CI: a missing database must fail, not skip
            raise
        pytest.skip("Postgres ishlamayapti: `docker compose up -d postgres`")
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    config.attributes["configure_logger"] = False
    command.downgrade(config, "base")  # also proves every migration can be rolled back
    command.upgrade(config, "head")
    return TEST_DATABASE_URL


@pytest.fixture
async def session_factory(
    migrated_database: str,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_engine(migrated_database)
    yield create_session_factory(engine)
    async with engine.begin() as connection:
        # Everything references users, so this empties all business tables (not regions).
        await connection.execute(text("TRUNCATE users CASCADE"))
    await engine.dispose()


@pytest.fixture
def uow_factory(session_factory: async_sessionmaker[AsyncSession]) -> UowFactory:
    return lambda: SqlAlchemyUnitOfWork(session_factory)
