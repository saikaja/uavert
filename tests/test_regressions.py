"""Regression tests for the issues found in the phase 5 code review."""

from datetime import UTC, datetime, timedelta

import h3
import pytest

from uavert import db
from uavert.ingest import crime, live, news as news_ingest
from uavert.ingest.runs import ensure_reference_rows
from uavert.scoring.build import cell_scores
from uavert.sources import news
from uavert.sources.eccc import AlertRecord
from uavert.sources.geocode import Place
from uavert.sources.http import SourceUnavailable

NOW = datetime(2026, 10, 1, 18, tzinfo=UTC)


@pytest.fixture
async def conn_and_region(test_db_url):
    conn = await db.connect(test_db_url)
    yield conn, await ensure_reference_rows(conn)
    await conn.execute("DELETE FROM news_events WHERE url LIKE 'https://example.test/r%' OR url LIKE 'javascript:%'")
    await conn.execute("DELETE FROM official_alerts WHERE external_id LIKE 'REG-%'")
    await conn.execute("DELETE FROM neighbourhoods WHERE external_id = 'REG'")
    await conn.close()


class Geocoder:
    def __init__(self, down=False):
        self.down, self.calls = down, 0

    async def search(self, query):
        self.calls += 1
        if self.down:
            raise SourceUnavailable("down")
        return Place("Jane and Finch", -79.52, 43.76)


@pytest.mark.db
async def test_news_rerun_keeps_location_and_skips_geocoding(conn_and_region):
    conn, region_id = conn_and_region
    await conn.execute(
        "INSERT INTO neighbourhoods (region_id, external_id, name, valid_year, geom) VALUES ($1, 'REG', 'Reg',"
        " 2025, ST_GeomFromText('MULTIPOLYGON(((-79.53 43.75,-79.51 43.75,-79.51 43.77,-79.53 43.77,-79.53 43.75)))', 4326))",
        region_id)
    item = news.NewsItem("news_cbc", "CBC News", "Man injured in shooting near Jane and Finch", "",
                         "https://example.test/r1", NOW - timedelta(hours=1))
    await news_ingest.store(conn, region_id, [item], Geocoder(), now=NOW)
    second = Geocoder(down=True)
    await news_ingest.store(conn, region_id, [item], second, now=NOW)
    row = await conn.fetchrow("SELECT h3, location_text FROM news_events WHERE url = 'https://example.test/r1'")
    assert row["h3"] is not None and row["location_text"] == "Jane and Finch"
    assert second.calls == 0  # already located: no new geocoding call


@pytest.mark.db
async def test_news_ignores_non_web_links(conn_and_region):
    conn, region_id = conn_and_region
    item = news.NewsItem("news_gdelt", "x", "Shooting in Toronto", "", "javascript:alert(1)", NOW)
    assert await news_ingest.store(conn, region_id, [item], Geocoder(), now=NOW) == 0


@pytest.mark.db
async def test_alert_withdrawn_from_feed_is_marked_ended(conn_and_region):
    conn, region_id = conn_and_region
    poly = {"type": "Polygon", "coordinates": [[[-79.4, 43.6], [-79.3, 43.6], [-79.3, 43.7], [-79.4, 43.6]]]}
    warning = AlertRecord("REG-1", "warning", None, "test warning", "red", "issued", NOW, None, None, poly)
    await live.store_alerts(conn, region_id, [warning])
    await live.store_alerts(conn, region_id, [])  # next collection: no longer in the feed
    assert await conn.fetchval("SELECT status FROM official_alerts WHERE external_id = 'REG-1'") == "ended"


@pytest.mark.db
async def test_crime_source_with_no_records_does_not_crash(conn_and_region, monkeypatch):
    conn, region_id = conn_and_region

    async def nothing(client, source_key):
        return []
    monkeypatch.setattr(crime, "fetch", nothing)
    await crime.run(conn, None, region_id)
    assert await conn.fetchval("SELECT last_status FROM sources WHERE key = 'tps_homicides'") == "ok"


def test_build_without_street_incidents_says_what_to_do():
    cell = h3.latlng_to_cell(43.65, -79.38, 9)
    with pytest.raises(ValueError, match="Run `uavert ingest crime` first"):
        cell_scores([], {cell: 1}, {1: "Test"}, {})
