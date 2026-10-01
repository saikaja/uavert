"""Address search with OpenStreetMap Nominatim: preferring Toronto, at most 1 request per second
(Nominatim's usage policy). Answers are kept in memory and, when a database is given, saved for
30 days so restarts and new hosted instances reuse them."""

import asyncio
import re
import time
from dataclasses import dataclass

import httpx

from uavert.config import get_settings
from uavert.sources.http import get_json

TORONTO_VIEWBOX = "-79.64,43.86,-79.11,43.58"  # left,top,right,bottom
CACHE_TTL_S = 24 * 3600  # in memory
SAVED_DAYS = 30  # in the database
LATLON = re.compile(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")


@dataclass(frozen=True)
class Place:
    display_name: str
    lon: float
    lat: float


def parse_latlon(text: str) -> Place | None:
    """'43.65,-79.38' -> Place; anything else -> None."""
    m = LATLON.match(text)
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return Place(f"{lat:.5f}, {lon:.5f}", lon, lat)


class Geocoder:
    def __init__(self, client: httpx.AsyncClient, base_url: str | None = None, db=None):
        """`db`: an asyncpg pool or connection for saved lookups; None keeps answers in memory only."""
        self._client = client
        self._url = (base_url or get_settings().nominatim_url).rstrip("/") + "/search"
        self._db = db
        self._cache: dict[str, tuple[float, Place | None]] = {}
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def search(self, query: str) -> Place | None:
        """The best match, or None when nothing is found. Raises SourceUnavailable if Nominatim is down."""
        key = " ".join(query.lower().split())
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
            return hit[1]
        saved = await self._saved(key)
        if saved is not None:
            self._remember(key, saved[1])
            return saved[1]
        async with self._lock:
            wait = 1.0 - (time.monotonic() - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
            results = await get_json(self._client, self._url, {
                "q": query, "format": "jsonv2", "limit": 1, "countrycodes": "ca",
                "viewbox": TORONTO_VIEWBOX, "bounded": 0,
            })
        place = Place(results[0]["display_name"], float(results[0]["lon"]), float(results[0]["lat"])) if results else None
        self._remember(key, place)
        await self._save(key, place)
        return place

    def _remember(self, key: str, place: Place | None) -> None:
        now = time.monotonic()
        if len(self._cache) > 5_000:  # drop expired entries
            self._cache = {k: v for k, v in self._cache.items() if now - v[0] < CACHE_TTL_S}
        self._cache[key] = (now, place)

    async def _saved(self, key: str) -> tuple[bool, Place | None] | None:
        """(found, place) from the database, or None if there is no saved answer."""
        if self._db is None:
            return None
        row = await self._db.fetchrow(
            "SELECT found, display_name, lon, lat FROM geocode_cache"
            " WHERE query_key = $1 AND collected_at > now() - make_interval(days => $2)", key, SAVED_DAYS)
        if row is None:
            return None
        return row["found"], (Place(row["display_name"], row["lon"], row["lat"]) if row["found"] else None)

    async def _save(self, key: str, place: Place | None) -> None:
        if self._db is None:
            return
        await self._db.execute(
            "INSERT INTO geocode_cache (query_key, found, display_name, lon, lat) VALUES ($1, $2, $3, $4, $5)"
            " ON CONFLICT (query_key) DO UPDATE SET found = $2, display_name = $3, lon = $4, lat = $5,"
            " collected_at = now()",
            key, place is not None, place.display_name if place else None, place.lon if place else None,
            place.lat if place else None)
