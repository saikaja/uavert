import pytest

from uavert.config import get_settings

TEST_DB_URL = get_settings().test_database_url


@pytest.fixture(scope="session")
async def test_db_url():
    """The Neon test branch, migrated to the latest schema."""
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    from uavert import db

    conn = await db.connect(TEST_DB_URL)
    try:
        await db.migrate(conn)
    finally:
        await conn.close()
    return TEST_DB_URL


@pytest.fixture(scope="session")
async def test_pool(test_db_url):
    from uavert import db

    pool = await db.create_pool(test_db_url)
    yield pool
    await pool.close()


@pytest.fixture(scope="session")
async def client(test_pool):
    import httpx

    from uavert.api.app import app

    app.state.pool = test_pool
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c

