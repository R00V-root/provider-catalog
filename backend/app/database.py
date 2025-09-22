from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base

engine = create_async_engine(settings.database_url, echo=settings.debug, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def lifespan(app):
    """Ensure database resources are ready when the app starts."""

    try:
        yield
    finally:
        await engine.dispose()
