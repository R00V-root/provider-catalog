from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


DbSessionDep = Depends(get_db_session)
