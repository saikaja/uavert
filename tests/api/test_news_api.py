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


# ---- 01-03-news.md: windows by type (37), trending (39), never scored (41) ----

@pytest.fixture
async def typed_rows(test_pool, seeded):
    now = datetime.now(UTC)
    region_id = await test_pool.fetchval("SELECT id FROM regions WHERE code = 'CA-ON-TOR'")
    rows = [  # (url, publisher, source, category, headline, age, located on Test East)
        ("p-new", "CBC News", "news_cbc", "protest", "Test protest", timedelta(days=1), False),
        ("p-old", "CBC News", "news_cbc", "protest", "Older test protest", timedelta(days=3), False),
        ("v-6d", "CityNews", "news_citynews", "violent_incident", "Test stabbing", timedelta(days=6), False),
        ("v-8d", "CityNews", "news_citynews", "violent_incident", "Older test stabbing", timedelta(days=8), False),
        ("b-50d", "Toronto Star", "news_star", "property_crime", "Test break-ins reported", timedelta(days=50), False),
        ("b-70d", "Toronto Star", "news_star", "property_crime", "Older test break-ins", timedelta(days=70), False),
        # a fresh, located property story next to Test East's cells: listed, never scored
        ("b-here", "Global News", "news_global", "property_crime", "Catalytic converter thefts at Test East depot",
         timedelta(hours=1), True),
        ("b-here-2", "Toronto Star", "news_star", "property_crime", "Test East depot catalytic converter thefts continue",
         timedelta(hours=2), False),
        ("b-here-3", "CBC News", "news_cbc", "property_crime", "Arrest in Test East depot catalytic converter thefts",
         timedelta(hours=3), False),
    ]
    for url, publisher, source, category, headline, age, located in rows:
        await test_pool.execute(
            "INSERT INTO news_events (region_id, source_key, url, headline, publisher, category, geom, h3, published_at)"
            " VALUES ($1, $2, $3, $4, $5, $6,"
            " CASE WHEN $8 THEN ST_SetSRID(ST_MakePoint(-79.375, 43.655), 4326) END,"
            " CASE WHEN $8 THEN h3_lat_lng_to_cell(point(-79.375, 43.655), 9) END, $7)",
            region_id, source, f"https://example.test/{url}", headline, publisher, category, now - age, located)
    yield
    await test_pool.execute("DELETE FROM news_events WHERE url LIKE 'https://example.test/%'")


async def test_news_events_by_type_use_each_types_window(client, typed_rows):
    items = (await client.get("/api/v1/news-events", params={"window": "by_type"})).json()["data"]
    got = {i["url"].rsplit("/", 1)[1]: i["window_days"] for i in items}
    assert got == {"p-new": 2, "v-6d": 7, "b-50d": 60, "b-here": 60, "b-here-2": 60, "b-here-3": 60}
    r = await client.get("/api/v1/news-events", params={"window": "all"})
    assert r.status_code == 422


async def test_trending_groups_one_event_across_outlets(client, typed_rows):
    data = (await client.get("/api/v1/news-trending")).json()["data"]
    assert len(data) == 1
    t = data[0]
    assert (t["story_count"], t["outlet_count"], t["category"]) == (3, 3, "property_crime")
    assert t["headline"] == "Catalytic converter thefts at Test East depot"  # the newest leads


async def test_property_crime_news_never_changes_a_score(client, seeded, typed_rows):
    d = (await client.get(f"/api/v1/neighbourhoods/{seeded['T2']}")).json()["data"]
    assert d["categories"]["news"] == 0 and not any(x["category"] == "news" for x in d["reasons"])
    cell = (await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.375})).json()["data"]["street"]
    assert cell["categories"]["news"] == 0
