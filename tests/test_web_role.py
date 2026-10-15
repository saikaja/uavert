"""The website's read-only database user on the test branch (01-03-security.md, criterion 46)."""

import asyncpg
import pytest

from uavert import db
from uavert.config import get_settings

pytestmark = pytest.mark.db
WEB_URL = get_settings().test_web_database_url


@pytest.fixture
async def web(test_db_url):
    if not WEB_URL:
        pytest.skip("TEST_WEB_DATABASE_URL is not set (scripts/create_web_role.py)")
    conn = await db.connect(WEB_URL)
    yield conn
    await conn.close()


async def test_is_the_web_user_without_neon_superuser(web):
    assert await web.fetchval("SELECT current_user") == "uavert_web"
    assert not await web.fetchval("SELECT rolsuper OR rolcreaterole OR rolcreatedb FROM pg_roles WHERE rolname = current_user")
    assert not await web.fetchval("SELECT pg_has_role('uavert_web', 'neon_superuser', 'MEMBER')"
                                  " FROM pg_roles WHERE rolname = 'neon_superuser'")


@pytest.mark.parametrize("table", ["neighbourhoods", "neighbourhood_scores", "cell_scores", "news_events", "crime_patterns",
                                   "sources", "incidents", "activity_by_hour"])
async def test_can_read_every_table_the_website_uses(web, table):
    await web.fetchval(f"SELECT count(*) FROM {table}")


async def test_can_save_lookups(web):
    try:
        await web.execute("INSERT INTO geocode_cache (query_key, found) VALUES ('web-role-test', false)"
                          " ON CONFLICT (query_key) DO UPDATE SET found = false")
        await web.execute("INSERT INTO route_cache (route_key, coordinates, distance_m, duration_s)"
                          " VALUES ('web-role-test', '[]', 1, 1) ON CONFLICT (route_key) DO UPDATE SET distance_m = 1")
    finally:
        owner = await db.connect(get_settings().test_database_url)
        await owner.execute("DELETE FROM geocode_cache WHERE query_key = 'web-role-test'")
        await owner.execute("DELETE FROM route_cache WHERE route_key = 'web-role-test'")
        await owner.close()


@pytest.mark.parametrize("sql", [
    "INSERT INTO incidents (event_id) VALUES ('x')",
    "DELETE FROM neighbourhoods",
    "UPDATE neighbourhood_scores SET crime_score = 0",
    "DELETE FROM geocode_cache",
    "TRUNCATE news_events",
    "CREATE TABLE web_role_test (x int)",
    "DROP TABLE crime_patterns",
])
async def test_cannot_change_data_or_schema(web, sql):
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await web.execute(sql)
