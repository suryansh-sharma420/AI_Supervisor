import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
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
        poolclass=NullPool,
        # Prevent infinite hangs if a database lock occurs
        connect_args={"command_timeout": 10}
    )
    
    print("\n[DB SETUP] Connecting to test database...")
    async with engine.begin() as conn:
        print("[DB SETUP] Resetting test database (drop/create)...")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # We skip drop_all in teardown because it often hangs on zombie async connections.
    # The setup phase of the next run will handle the cleanup.
    print("\n[DB TEARDOWN] Disposing engine...")
    await engine.dispose()
    print("[DB TEARDOWN] Engine disposed.")

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
        try:
            await session.rollback()
        except Exception:
            pass

@pytest_asyncio.fixture(autouse=True)
async def override_get_db(engine):
    """Override the get_db dependency for all API tests."""
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async def _get_test_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def ensure_groq_client_in_app():
    """Ensure app.state.groq_client exists and returns serializable content."""
    from unittest.mock import AsyncMock, MagicMock
    if not hasattr(app.state, "groq_client"):
        mock = AsyncMock()
        # Ensure that any LLM calls return a mock structure that results in a string
        # This prevents SQLAlchemy from trying to save MagicMock objects into JSONB columns
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Global Mock Summary"
        mock.chat.completions.create.return_value = mock_resp
        
        app.state.groq_client = mock
    yield
