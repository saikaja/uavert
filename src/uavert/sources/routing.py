"""Walking routes from an OSRM server (default: the FOSSGIS OpenStreetMap foot router). Routes are
kept in memory and, when a database is given, saved for 7 days."""

import json
from dataclasses import dataclass

import httpx

from uavert.config import get_settings
from uavert.sources.geocode import Place
from uavert.sources.http import SourceUnavailable, get

SAVED_DAYS = 7


class NoRoute(Exception):
    """The router found no walking route between the two points."""


@dataclass(frozen=True)
class Route:
    coordinates: list[tuple[float, float]]  # (lon, lat)
    distance_m: float
    duration_s: float


def route_key(start: Place, end: Place) -> str:
    return f"{start.lon:.5f},{start.lat:.5f};{end.lon:.5f},{end.lat:.5f}"


class Router:
    def __init__(self, client: httpx.AsyncClient, base_url: str | None = None, db=None):
        """`db`: an asyncpg pool or connection for saved routes; None keeps routes in memory only."""
        self._client = client
        self._url = (base_url or get_settings().osrm_url).rstrip("/")
        self._db = db
        self._memory: dict[str, Route] = {}

    async def walk(self, start: Place, end: Place) -> Route:
        key = route_key(start, end)
        if key in self._memory:
            return self._memory[key]
        route = await self._saved(key) or await self._fetch(start, end)
        if len(self._memory) > 2_000:
            self._memory.clear()
        self._memory[key] = route
        return route

    async def _fetch(self, start: Place, end: Place) -> Route:
        url = f"{self._url}/route/v1/foot/{start.lon},{start.lat};{end.lon},{end.lat}"
        r = await get(self._client, url, {"overview": "full", "geometries": "geojson"}, accept_client_errors=True)
        try:
            data = r.json()
        except ValueError as e:
            raise SourceUnavailable(f"{url}: response was not JSON") from e
        if data.get("code") in ("NoRoute", "NoSegment"):
            raise NoRoute(data.get("message") or data["code"])
        if data.get("code") != "Ok" or not data.get("routes"):
            raise SourceUnavailable(f"{url}: {data.get('code')} {data.get('message', '')}")
        best = data["routes"][0]
        route = Route([tuple(c) for c in best["geometry"]["coordinates"]], best["distance"], best["duration"])
        if self._db is not None:
            await self._db.execute(
                "INSERT INTO route_cache (route_key, coordinates, distance_m, duration_s) VALUES ($1, $2::jsonb, $3, $4)"
                " ON CONFLICT (route_key) DO UPDATE SET coordinates = EXCLUDED.coordinates, distance_m = $3,"
                " duration_s = $4, collected_at = now()",
                route_key(start, end), json.dumps(route.coordinates), route.distance_m, route.duration_s)
        return route

    async def _saved(self, key: str) -> Route | None:
        if self._db is None:
            return None
        row = await self._db.fetchrow(
            "SELECT coordinates, distance_m, duration_s FROM route_cache"
            " WHERE route_key = $1 AND collected_at > now() - make_interval(days => $2)", key, SAVED_DAYS)
        if row is None:
            return None
        return Route([tuple(c) for c in json.loads(row["coordinates"])], row["distance_m"], row["duration_s"])
