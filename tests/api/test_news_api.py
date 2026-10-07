from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.db


@pytest.fixture
async def news_rows(test_pool, seeded):
    now = datetime.now(UTC)
    region_id = await test_pool.fetchval("SELECT id FROM regions WHERE code = 'CA-ON-TOR'")
    await test_pool.execute(
        "INSERT INTO news_events (region_id, source_key, url, headline, publisher, category, location_text, geom, h3, published_at)"
        " VALUES ($1, 'news_cbc', 'https://example.test/located', 'Test shooting near Test Centre', 'CBC News',"
        " 'violent_incident', 'Test Centre', ST_SetSRID(ST_MakePoint(-79.385, 43.655), 4326),"
        " h3_lat_lng_to_cell(point(-79.385, 43.655), 9), $2),"
        " ($1, 'news_cbc', 'https://example.test/citywide', 'Test protest planned', 'CBC News', 'protest', NULL, NULL, NULL, $2),"
        " ($1, 'news_cbc', 'https://example.test/old', 'Old test story', 'CBC News', 'protest', NULL, NULL, NULL, $3)",
        region_id, now - timedelta(hours=1), now - timedelta(days=3),
    )
    yield
    await test_pool.execute("DELETE FROM news_events WHERE url LIKE 'https://example.test/%'")


async def test_news_events_lists_recent_reports_unverified(client, news_rows):
    r = await client.get("/api/v1/news-events")
    assert r.status_code == 200
    items = {i["url"]: i for i in r.json()["data"]}
    assert set(items) == {"https://example.test/located", "https://example.test/citywide"}
    assert items["https://example.test/citywide"]["citywide"] is True
    assert items["https://example.test/located"]["lat"] == pytest.approx(43.655)
    assert all(i["verified"] is False and i["published_at"] and i["collected_at"] for i in items.values())


async def test_located_report_raises_its_neighbourhood_with_unverified_reason(client, seeded, news_rows):
    d = (await client.get(f"/api/v1/neighbourhoods/{seeded['T2']}")).json()["data"]  # crime 20, no report inside
    assert d["categories"]["news"] == 0
    d = (await client.get(f"/api/v1/neighbourhoods/{seeded['T1']}")).json()["data"]
    assert d["categories"]["news"] > 60
    news_reason = next(x for x in d["reasons"] if x["category"] == "news")
    assert news_reason["text"].startswith("Unverified news report: Test shooting near Test Centre")
    assert news_reason["url"] == "https://example.test/located"


@pytest.mark.parametrize("params", [{"since_hours": 0}, {"limit": 1000}])
async def test_news_events_validates_ranges(client, seeded, params):
    r = await client.get("/api/v1/news-events", params=params)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
