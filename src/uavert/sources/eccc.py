"""Environment and Climate Change Canada (MSC GeoMet OGC API): AQHI observations and weather alerts."""

import json
from dataclasses import dataclass
from datetime import datetime

import httpx

from uavert.sources.http import SourceUnavailable, get_json

API = "https://api.weather.gc.ca/collections"
TORONTO_BBOX = "-79.70,43.55,-79.10,43.90"  # includes stations just outside the city, for nearest-station lookup


@dataclass(frozen=True)
class AqhiReading:
    station_id: str
    station_name: str
    lon: float
    lat: float
    observed_at: datetime
    aqhi: float


@dataclass(frozen=True)
class AlertRecord:
    external_id: str
    alert_type: str
    alert_code: str | None
    name: str
    risk_colour: str | None
    status: str
    issued_at: datetime
    expires_at: datetime | None
    text: str | None
    geometry: dict  # GeoJSON


def _time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def parse_aqhi(feature: dict) -> AqhiReading:
    p = feature["properties"]
    lon, lat = feature["geometry"]["coordinates"][:2]
    return AqhiReading(p["location_id"], p["location_name_en"], lon, lat, _time(p["observation_datetime"]), float(p["aqhi"]))


def parse_alert(feature: dict) -> AlertRecord:
    p = feature["properties"]
    return AlertRecord(
        external_id=str(feature["id"]),
        alert_type=p["alert_type"],
        alert_code=p.get("alert_code"),
        name=p.get("alert_name_en") or p.get("alert_short_name_en") or "weather alert",
        risk_colour=p.get("risk_colour_en"),
        status=p.get("status_en") or "issued",
        issued_at=_time(p.get("publication_datetime") or p.get("validity_datetime")),
        expires_at=_time(p.get("expiration_datetime") or p.get("event_end_datetime")),
        text=p.get("alert_text_en"),
        geometry=feature["geometry"],
    )


async def _items(client: httpx.AsyncClient, collection: str, extra: dict) -> list[dict]:
    data = await get_json(client, f"{API}/{collection}/items", {"f": "json", "bbox": TORONTO_BBOX, "limit": 500, **extra})
    if "features" not in data:
        raise SourceUnavailable(f"{collection}: unexpected response {json.dumps(data)[:200]}")
    return data["features"]


async def fetch_aqhi(client: httpx.AsyncClient) -> list[AqhiReading]:
    return [parse_aqhi(f) for f in await _items(client, "aqhi-observations-realtime", {"latest": "true"})]


async def fetch_alerts(client: httpx.AsyncClient) -> list[AlertRecord]:
    return [parse_alert(f) for f in await _items(client, "weather-alerts", {})]
