"""Live conditions loaded once per request and applied to any point: nearest AQHI station,
active official alerts and located news reports, combined with a stored crime score."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from uavert.freshness import iso, source_dates
from uavert.scoring import alerts as alert_rules
from uavert.scoring import heat as heat_rules
from uavert.scoring import news as news_rules
from uavert.scoring.combine import Reason, Score, combine
from uavert.scoring.environment import STALE_AFTER, environment
from uavert.scoring.route import distance_m


TORONTO_TZ = ZoneInfo("America/Toronto")


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
    news: list[news_rules.NewsSignal] = field(default_factory=list)
    activity: list[tuple[float, str]] = field(default_factory=list)  # (people out vs daytime, basis) by hour
    cool_spaces: list[heat_rules.CoolSpace] = field(default_factory=list)  # loaded only while a heat alert is active

    def nearest_station(self, lon: float, lat: float) -> Station | None:
        current = [s for s in self.stations if self.now - s.observed_at <= STALE_AFTER] or self.stations
        return min(current, key=lambda s: distance_m((lon, lat), (s.lon, s.lat)), default=None)

    def score(self, lon: float, lat: float, crime_score: int, crime_reasons: list[dict],
              cell: str | None = None, neighbourhood_id: int | None = None, when: datetime | None = None) -> Score:
        """Combine a stored crime score with live conditions at a point. News applies to a street
        `cell` (reports within about 500 m) or a `neighbourhood_id` (reports inside it). `when` (Toronto
        local time) is the moment opening hours are checked at; default now."""
        station = self.nearest_station(lon, lat)
        env, env_reasons = environment(
            station.name if station else None, station.aqhi if station else None,
            station.observed_at if station else None, self.sources.get("eccc_aqhi", {}).get("collected_at"), self.now)
        point = Point(lon, lat)
        covering = [a for a, g in self.alerts if g.covers(point)]
        alert, alert_reasons = alert_rules.alert_score(covering, self.now)
        heat = next((a for a in covering if heat_rules.is_heat_alert(a.name) and alert_rules.is_active(a, self.now)), None)
        if heat and self.cool_spaces:
            alert_reasons.insert(1, heat_rules.heat_reason(
                heat.name, self.cool_spaces, lon, lat, when or self.now.astimezone(TORONTO_TZ),
                self.sources.get("toronto_cool_spaces", {}).get("collected_at")))
        news, news_reasons = news_rules.news_score(self.news, self.now, cell, neighbourhood_id)
        reasons = [Reason(**r) for r in crime_reasons] + env_reasons + alert_reasons + news_reasons
        return combine({"crime": crime_score, "environment": env, "alert": alert, "news": news}, reasons)


async def load(pool: asyncpg.Pool, now: datetime | None = None) -> LiveContext:
    now = now or datetime.now(UTC)
    ctx = LiveContext(now=now, sources=await source_dates(pool))
    for r in await pool.fetch(
        "SELECT DISTINCT ON (station_id) station_name, ST_X(geom) AS lon, ST_Y(geom) AS lat, observed_at, aqhi"
        " FROM aqhi_readings WHERE observed_at > $1::timestamptz - interval '2 days' ORDER BY station_id, observed_at DESC", now
    ):
        ctx.stations.append(Station(r["station_name"], r["lon"], r["lat"], r["observed_at"], float(r["aqhi"])))
    for r in await pool.fetch(
        "SELECT name, alert_type, risk_colour, status, issued_at, expires_at, collected_at, ST_AsGeoJSON(geom) AS g"
        " FROM official_alerts WHERE status <> 'ended' AND (expires_at IS NULL OR expires_at > $1)", now
    ):
        a = alert_rules.Alert(r["name"], r["alert_type"], r["risk_colour"], r["status"], r["issued_at"],
                              r["expires_at"], iso(r["collected_at"]))
        ctx.alerts.append((a, shape(json.loads(r["g"]))))
    for r in await pool.fetch(
        "SELECT e.headline, e.url, e.publisher, e.category, e.published_at, e.h3::text AS h3, e.collected_at,"
        " c.neighbourhood_id FROM news_events e LEFT JOIN cells c ON c.h3 = e.h3"
        " WHERE e.h3 IS NOT NULL AND e.published_at > $1", now - timedelta(hours=news_rules.WINDOW_HOURS)
    ):
        ctx.news.append(news_rules.NewsSignal(r["headline"], r["url"], r["publisher"], r["category"],
                                              r["published_at"], r["h3"], r["neighbourhood_id"], iso(r["collected_at"])))
    ctx.activity = [(float(r["factor_used"]), r["basis"])
                    for r in await pool.fetch("SELECT factor_used, basis FROM activity_by_hour ORDER BY hour")]
    if any(heat_rules.is_heat_alert(a.name) for a, _ in ctx.alerts):
        ctx.cool_spaces = [heat_rules.CoolSpace(r["name"], r["kind"], r["lon"], r["lat"], json.loads(r["hours"]))
                           for r in await pool.fetch("SELECT name, kind, ST_X(geom) AS lon, ST_Y(geom) AS lat, hours"
                                                     " FROM cool_spaces")]
    return ctx


def envelope(data, ctx: LiveContext) -> dict:
    return {"data": data, "meta": {"generated_at": ctx.now.isoformat(), "sources": ctx.sources}}
