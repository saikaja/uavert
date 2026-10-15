"""Edge caching headers (01-03-security.md, criterion 43)."""

import pytest

pytestmark = pytest.mark.db
CACHED = "public, max-age=0, s-maxage=300, stale-while-revalidate=300"


@pytest.mark.parametrize("path", ["/api/v1/neighbourhoods", "/api/v1/news-trending", "/api/v1/crime-patterns",
                                  "/api/v1/sources", "/api/v1/scoring-rules"])
async def test_successful_api_gets_are_cached_at_the_edge(client, seeded, path):
    r = await client.get(path)
    assert r.status_code == 200 and r.headers["cache-control"] == CACHED


async def test_errors_are_never_cached(client, seeded):
    r = await client.get("/api/v1/neighbourhoods", params={"hour": 24})
    assert r.status_code == 422 and "s-maxage" not in r.headers.get("cache-control", "")
    r = await client.get("/api/v1/neighbourhoods/999999")
    assert r.status_code == 404 and "s-maxage" not in r.headers.get("cache-control", "")


async def test_health_is_never_cached(client, seeded):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200 and "s-maxage" not in r.headers.get("cache-control", "")


async def test_pages_are_not_given_the_api_cache_header(client, seeded):
    r = await client.get("/")
    assert "s-maxage" not in r.headers.get("cache-control", "")
