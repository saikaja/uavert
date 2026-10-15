"""News ingestion: classify each story, locate it in Toronto when possible, store the labelled ones."""

from datetime import UTC, datetime, timedelta

import asyncpg
import httpx

from uavert.config import get_settings
from uavert.ingest.runs import ingest_run
from uavert.scoring.news import DISPLAY_DAYS
from uavert.sources import news
from uavert.sources.geocode import Geocoder
from uavert.sources.http import SourceUnavailable

async def store(conn: asyncpg.Connection, region_id: int, items: list[news.NewsItem], geocoder: Geocoder,
                now: datetime | None = None) -> int:
    """Store labelled stories still inside their type's listing window (DISPLAY_DAYS). Located outside Toronto ->
    skipped; no usable location -> stored as citywide (listed, but never changes a score)."""
    now = now or datetime.now(UTC)
    names = [r["name"] for r in await conn.fetch("SELECT name FROM neighbourhoods WHERE region_id = $1", region_id)]
    located = {r["url"] for r in await conn.fetch("SELECT url FROM news_events WHERE geom IS NOT NULL")}
    stored = 0
    for item in items:
        category = news.classify(item.headline, item.summary, year=item.published_at.year)
        if (category is None or now - item.published_at > timedelta(days=DISPLAY_DAYS[category])
                or not item.url.startswith(("https://", "http://"))):
            continue
        place_text = news.extract_place(f"{item.headline}. {item.summary}", names)
        lon = lat = None
        if place_text and item.url not in located:
            try:
                place = await geocoder.search(f"{place_text}, Toronto, Ontario")
            except SourceUnavailable:
                place = None  # keep the story as citywide rather than lose it
            if place:
                inside = await conn.fetchval(
                    "SELECT EXISTS (SELECT 1 FROM neighbourhoods WHERE region_id = $1"
                    " AND ST_Covers(geom, ST_SetSRID(ST_MakePoint($2, $3), 4326)))", region_id, place.lon, place.lat)
                if not inside:
                    continue
                lon, lat = place.lon, place.lat
        await conn.execute(
            "INSERT INTO news_events (region_id, source_key, url, headline, publisher, category, location_text,"
            " geom, h3, published_at) VALUES ($1, $2, $3, $4, $5, $6, $7,"
            " CASE WHEN $8::float8 IS NULL THEN NULL ELSE ST_SetSRID(ST_MakePoint($8, $9), 4326) END,"
            " CASE WHEN $8::float8 IS NULL THEN NULL ELSE h3_lat_lng_to_cell(point($8, $9), 9) END, $10)"
            # A story located before keeps its location if this run couldn't (or didn't need to) locate it.
            " ON CONFLICT (url) DO UPDATE SET headline = $4, category = $6,"
            " location_text = COALESCE(EXCLUDED.location_text, news_events.location_text),"
            " geom = COALESCE(EXCLUDED.geom, news_events.geom), h3 = COALESCE(EXCLUDED.h3, news_events.h3),"
            " last_seen_at = now()",
            region_id, item.source_key, item.url, item.headline, item.publisher, category, place_text, lon, lat,
            item.published_at,
        )
        stored += 1
    return stored


async def _run(conn, client, region_id, source_key, fetch) -> None:
    async with ingest_run(conn, source_key) as r:
        items = await fetch(client)
        r.rows_written = await store(conn, region_id, items, Geocoder(client, get_settings().nominatim_url, db=conn))
        r.data_as_of = max((i.published_at for i in items), default=None)
        print(f"    {source_key}: {len(items)} stories read, {r.rows_written} labelled as protest, violent incident"
              " or property crime")


async def relabel(conn: asyncpg.Connection, client: httpx.AsyncClient | None = None, region_id: int | None = None) -> None:
    """Remove stored stories the current rules exclude (01-03-news.md): sport, an event in an earlier year, other
    regions. Only headlines are stored, so types aren't changed here: the summary that set them is gone."""
    since = datetime.now(UTC) - timedelta(days=max(DISPLAY_DAYS.values()))
    removed = 0
    for r in await conn.fetch("SELECT id, headline, published_at FROM news_events WHERE published_at > $1", since):
        if news.excluded(r["headline"], r["published_at"].year):
            await conn.execute("DELETE FROM news_events WHERE id = $1", r["id"])
            removed += 1
    print(f"    stored stories: {removed} removed under the current rules")


def rss_step(source_key: str):
    """The ingest step for one RSS feed; each feed is its own source, so one failing leaves the others."""
    async def run(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> None:
        await _run(conn, client, region_id, source_key, lambda c: news.fetch_rss(c, source_key))
    return run


run_cbc = rss_step("news_cbc")


async def run_gdelt(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> None:
    await _run(conn, client, region_id, "news_gdelt", news.fetch_gdelt)
