"""Live conditions loaded once per request and applied to any point: nearest AQHI station,
active official alerts and (later) news, combined with a stored crime score."""

import json
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime

import asyncpg
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from uavert.scoring import alerts as alert_rules
from uavert.scoring.combine import Reason, Score, combine
from uavert.scoring.environment import STALE_AFTER, environment


@dataclass
class Station:
    name: str
    lon: float
    lat: float
    observed_at: datetime
    aqhi: float


@dataclass
class LiveContext:
    now: datetime
    sources: dict[str, dict]
    stations: list[Station] = field(default_factory=list)
    alerts: list[tuple[alert_rules.Alert, BaseGeometry]] = field(default_factory=list)

    def nearest_station(self, lon: float, lat: float) -> Station | None:
        current = [s for s in self.stations if self.now - s.observed_at <= STALE_AFTER] or self.stations
        return min(current, key=lambda s: _distance_km(lon, lat, s.lon, s.lat), default=None)

    def score(self, lon: float, lat: float, crime_score: int, crime_reasons: list[dict]) -> Score:
        station = self.nearest_station(lon, lat)
        env, env_reasons = environment(
            station.name if station else None, station.aqhi if station else None,
            station.observed_at if station else None, self.sources.get("eccc_aqhi", {}).get("collected_at"), self.now)
        point = Point(lon, lat)
        alert, alert_reasons = alert_rules.alert_score([a for a, g in self.alerts if g.covers(point)], self.now)
        reasons = [Reason(**r) for r in crime_reasons] + env_reasons + alert_reasons
        return combine({"crime": crime_score, "environment": env, "alert": alert}, reasons)


def _distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


async def load_sources(pool: asyncpg.Pool) -> dict[str, dict]:
    rows = await pool.fetch("SELECT key, data_as_of, last_collected_at FROM sources ORDER BY key")
    return {r["key"]: {"as_of": _iso(r["data_as_of"]), "collected_at": _iso(r["last_collected_at"])} for r in rows}


async def load(pool: asyncpg.Pool, now: datetime | None = None) -> LiveContext:
    now = now or datetime.now(UTC)
    ctx = LiveContext(now=now, sources=await load_sources(pool))
    for r in await pool.fetch(
        "SELECT DISTINCT ON (station_id) station_name, ST_X(geom) AS lon, ST_Y(geom) AS lat, observed_at, aqhi"
        " FROM aqhi_readings ORDER BY station_id, observed_at DESC"
    ):
        ctx.stations.append(Station(r["station_name"], r["lon"], r["lat"], r["observed_at"], float(r["aqhi"])))
    for r in await pool.fetch(
        "SELECT name, alert_type, risk_colour, status, issued_at, expires_at, collected_at, ST_AsGeoJSON(geom) AS g"
        " FROM official_alerts WHERE status <> 'ended' AND (expires_at IS NULL OR expires_at > $1)", now
    ):
        a = alert_rules.Alert(r["name"], r["alert_type"], r["risk_colour"], r["status"], r["issued_at"],
                              r["expires_at"], _iso(r["collected_at"]))
        ctx.alerts.append((a, shape(json.loads(r["g"]))))
    return ctx


def _iso(t: datetime | None) -> str | None:
    return t.isoformat() if t else None


def envelope(data, ctx: LiveContext) -> dict:
    return {"data": data, "meta": {"generated_at": ctx.now.isoformat(), "sources": ctx.sources}}
