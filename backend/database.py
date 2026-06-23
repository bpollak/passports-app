import os
import re as _re
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

_raw_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/passports",
)
DATABASE_URL = _re.sub(
    r"^postgres(?:ql)?(?:\+[a-z]+)?://",
    "postgresql+psycopg://",
    _raw_url,
)


class Base(DeclarativeBase):
    pass


def _make_engine():
    return create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


_sessionmaker = None


def get_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _sessionmaker


async def get_db():
    async with get_sessionmaker()() as session:
        yield session


async def init_db():
    engine = get_engine()
    async with engine.begin() as conn:
        from . import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
