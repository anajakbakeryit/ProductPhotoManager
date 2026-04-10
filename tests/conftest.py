"""
Test fixtures for backend API tests.
Uses SQLite async in-memory DB + httpx AsyncClient.
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.api.models.db import Base, User
from backend.api.deps import get_db, get_current_user
from backend.api.main import app


# In-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    async with TestSession() as session:
        yield session


# Fake admin user for tests
_fake_admin = User(id=1, username="testadmin", password_hash="x",
                   display_name="Test Admin", role="admin", is_active=True)


async def _override_get_current_user():
    return _fake_admin


@pytest_asyncio.fixture
async def client():
    """Async test client with DB + auth overrides."""
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    # Seed admin user
    async with TestSession() as db:
        db.add(User(id=1, username="testadmin", password_hash="x",
                    display_name="Test Admin", role="admin"))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_session():
    """Direct DB session for setup/assertions."""
    async with TestSession() as session:
        yield session
