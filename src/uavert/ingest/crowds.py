"""Big crowds: the reviewed venue list, and large City events found in the City's events calendar."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg
import httpx

from uavert.config import get_settings
from uavert.ingest.reference import DATA_DIR, read_csv
from uavert.ingest.runs import ingest_run
from uavert.sources import toronto_open_data as tod
from uavert.sources.geocode import Geocoder

TORONTO_TZ = ZoneInfo("America/Toronto")
LOOK_AHEAD_DAYS = 60


@dataclass(frozen=True)
class FoundEvent:
    event_key: str
    name: str
    pattern_key: str
    event_date: date
    location: str | None
    default_location: str


NOT_AN_ADDRESS = re.compile(r"^\s*(various|multiple|online|virtual|tbd|tba|city-?wide|see website)\b", re.I)


def match_large_events(raw: list[dict], patterns: list[dict], start: date, end: date) -> list[FoundEvent]:
    """Calendar entries whose name matches a reviewed large-event pattern, one per name and date within [start, end].

    The City calendar also lists small spin-offs ("... Artist Meet and Greet"). So when a pattern has featured
    entries, other entries count only on the dates a featured entry runs."""
    compiled = [(p, re.compile(p["pattern"], re.I)) for p in patterns]
    candidates = []
    featured_dates: dict[str, set[date]] = {}
    for e in raw:
        name = (e.get("event_name") or "").strip()
        pattern = next((p for p, rx in compiled if rx.search(name)), None)
        if pattern is None:
            continue
        featured = str(e.get("featured_event")).lower() == "yes"
        for d in e.get("event_dates") or []:
            if not d.get("date"):
                continue
            day = datetime.fromtimestamp(d["date"] / 1000, tz=UTC).astimezone(TORONTO_TZ).date()
            if not start <= day <= end:
                continue
            locations = d.get("locations") or []
            location = locations[0].split(":", 1)[-1].strip() if locations and isinstance(locations[0], str) else ""
            if not location or NOT_AN_ADDRESS.match(location):
                location = None
            if featured:
                featured_dates.setdefault(pattern["key"], set()).add(day)
            candidates.append((featured, FoundEvent(str(e.get("id") or e.get("calendar_id") or name), name,
                                                    pattern["key"], day, location, pattern["default_location"])))
    found = {}
    for featured, ev in candidates:
        dates = featured_dates.get(ev.pattern_key)
        if dates is not None and not featured and ev.event_date not in dates:
            continue  # a spin-off on a day the main event isn't running
        found.setdefault((ev.name.lower(), ev.event_date), ev)  # the calendar sometimes lists an event twice
    return list(found.values())


async def load_venues(conn: asyncpg.Connection, region_id: int, geocoder: Geocoder) -> int:
    rows = read_csv(DATA_DIR / "major_venues.csv")
    for v in rows:
        place = await geocoder.search(v["address"])
        if place is None:
            raise ValueError(f"Venue address not found: {v['address']}")
        await conn.execute(
            "INSERT INTO venues (name, region_id, address, capacity, source_url, geom)"
            " VALUES ($1, $2, $3, $4, $5, ST_SetSRID(ST_MakePoint($6, $7), 4326)) ON CONFLICT (name) DO UPDATE SET"
            " address = $3, capacity = $4, source_url = $5, geom = EXCLUDED.geom",
            v["name"], region_id, v["address"], int(v["capacity"]), v["source_url"], place.lon, place.lat)
    return len(rows)


async def load_events(conn: asyncpg.Connection, region_id: int, raw: list[dict], geocoder: Geocoder,
                      today: date) -> int:
    patterns = read_csv(DATA_DIR / "large_city_events.csv")
    events = match_large_events(raw, patterns, today - timedelta(days=1), today + timedelta(days=LOOK_AHEAD_DAYS))
    async def in_toronto(text: str | None):
        place = await geocoder.search(text) if text else None
        if place is None:
            return None
        inside = await conn.fetchval("SELECT EXISTS (SELECT 1 FROM neighbourhoods WHERE region_id = $1"
                                     " AND ST_Covers(geom, ST_SetSRID(ST_MakePoint($2, $3), 4326)))",
                                     region_id, place.lon, place.lat)
        return place if inside else None

    stored, kept = 0, []
    for e in events:
        place = await in_toronto(e.location) or await in_toronto(e.default_location)
        if place is None:
            continue
        kept.append(f"{e.event_key}|{e.event_date.isoformat()}")
        await conn.execute(
            "INSERT INTO crowd_events (event_key, event_date, region_id, name, pattern, location, geom)"
            " VALUES ($1, $2, $3, $4, $5, $6, ST_SetSRID(ST_MakePoint($7, $8), 4326))"
            " ON CONFLICT (event_key, event_date) DO UPDATE SET name = $4, pattern = $5, location = $6,"
            " geom = EXCLUDED.geom, last_seen_at = now()",
            e.event_key, e.event_date, region_id, e.name, e.pattern_key, e.location or e.default_location,
            place.lon, place.lat)
        stored += 1
    # Upcoming dates that no longer match (renamed, cancelled, or filtered out) are removed; past ones stay as history.
    await conn.execute("DELETE FROM crowd_events WHERE event_date >= $1 AND NOT (event_key || '|' || event_date = ANY($2::text[]))",
                       today - timedelta(days=1), kept)
    return stored


async def run(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> None:
    geocoder = Geocoder(client, get_settings().nominatim_url, db=conn)
    async with ingest_run(conn, "major_venues") as r:
        r.rows_written = await load_venues(conn, region_id, geocoder)
        r.data_as_of = datetime(2026, 10, 1, tzinfo=UTC)  # date the venue list was reviewed
    async with ingest_run(conn, "toronto_events") as r:
        raw = await tod.fetch_city_events(client)
        today = datetime.now(TORONTO_TZ).date()
        r.rows_written = await load_events(conn, region_id, raw, geocoder, today)
        r.data_as_of = datetime.now(UTC)
        print(f"    toronto_events: {len(raw):,} calendar entries read, {r.rows_written} large-event dates in the next {LOOK_AHEAD_DAYS} days")
