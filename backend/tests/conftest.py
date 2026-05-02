import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import Base
from app.models import Activity, Run, Supervisor  # noqa: F401

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a session-scoped engine with pooling disabled."""
    # NullPool ensures each connection is fresh and not reused from a pool
    engine = create_async_engine(
        settings.TEST_DATABASE_URL, 
        echo=False,
        poolclass=NullPool
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest_asyncio.fixture
async def db(engine) -> AsyncSession:
    """Provide a dedicated session for each test using the session engine."""
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        # Transaction is rolled back automatically by context manager on error, 
        # but we add an explicit rollback to be safe for next tests.
        try:
            await session.rollback()
        except Exception:
            pass
