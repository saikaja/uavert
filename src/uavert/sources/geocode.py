"""Address search with OpenStreetMap Nominatim: preferring Toronto, at most 1 request per second
(Nominatim's usage policy), with results cached for 24 hours."""

import asyncio
import re
import time
from dataclasses import dataclass

import httpx

from uavert.config import get_settings
from uavert.sources.http import get_json

TORONTO_VIEWBOX = "-79.64,43.86,-79.11,43.58"  # left,top,right,bottom
CACHE_TTL_S = 24 * 3600
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
    def __init__(self, client: httpx.AsyncClient, base_url: str | None = None):
        self._client = client
        self._url = (base_url or get_settings().nominatim_url).rstrip("/") + "/search"
        self._cache: dict[str, tuple[float, Place | None]] = {}
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def search(self, query: str) -> Place | None:
        """The best match, or None when nothing is found. Raises SourceUnavailable if Nominatim is down."""
        key = " ".join(query.lower().split())
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
            return hit[1]
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
        now = time.monotonic()
        if len(self._cache) > 5_000:  # drop expired entries
            self._cache = {k: v for k, v in self._cache.items() if now - v[0] < CACHE_TTL_S}
        self._cache[key] = (now, place)
        return place
