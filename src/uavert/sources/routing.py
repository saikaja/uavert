"""Walking routes from an OSRM server (default: the FOSSGIS OpenStreetMap foot router)."""

from dataclasses import dataclass

import httpx

from uavert.config import get_settings
from uavert.sources.geocode import Place
from uavert.sources.http import SourceUnavailable, get


class NoRoute(Exception):
    """The router found no walking route between the two points."""


@dataclass(frozen=True)
class Route:
    coordinates: list[tuple[float, float]]  # (lon, lat)
    distance_m: float
    duration_s: float


class Router:
    def __init__(self, client: httpx.AsyncClient, base_url: str | None = None):
        self._client = client
        self._url = (base_url or get_settings().osrm_url).rstrip("/")

    async def walk(self, start: Place, end: Place) -> Route:
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
        return Route([tuple(c) for c in best["geometry"]["coordinates"]], best["distance"], best["duration"])
