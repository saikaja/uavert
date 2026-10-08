"""Seed the Neon test branch with a tiny known dataset: 3 square neighbourhoods downtown,
their H3 cells, stored crime scores, one AQHI reading and one warning covering T3 only."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from uavert.ingest.reference import build_cells
from uavert.ingest.runs import ensure_reference_rows
from uavert.scoring.odds import odds
from uavert.scoring.trends import trends
from uavert.sources.tps import parse_crime_years

SQUARES = {  # external_id: (name, min_lon, min_lat, crime_score)
    "T1": ("Test Centre", -79.390, 43.650, 80),
    "T2": ("Test East", -79.380, 43.650, 20),
    "T3": ("Test Warning", -79.370, 43.650, 10),
}
# T1's odds: 20 serious violent, 50 assault, 130 property incidents among 10,000 residents; T2 and T3 have none stored
T1_ODDS = odds({"high": 20, "medium": 50, "low": 130, "any": 200}, 10_000,
               {"high": 60, "medium": 150, "low": 390, "any": 600}, 30_000, 2025)
# T1's trend: the real Yonge-Bay Corridor figures (tests/fixtures/tps/ncr_years_one.json); T2 and T3 have none stored
_YEARS = parse_crime_years(json.loads((Path(__file__).parents[1] / "fixtures" / "tps" / "ncr_years_one.json")
                                      .read_text())["attributes"], 2014, 2025)
_HOOD, _TORONTO = trends(_YEARS, 2025)
T1_TREND = _HOOD["170"] | {"toronto": _TORONTO, "source_key": "tps_ncr", "collected_at": "2026-10-08T15:32:17+00:00"}
SIZE = 0.01
STANDS_OUT = {"T1": 2.5, "T2": 1.0}  # vs_surroundings for each square's cells; T3: none (quiet surroundings)


def square(min_lon, min_lat, size=SIZE):
    return (f"MULTIPOLYGON((({min_lon} {min_lat},{min_lon + size} {min_lat},{min_lon + size} {min_lat + size},"
            f"{min_lon} {min_lat + size},{min_lon} {min_lat})))")


@pytest.fixture(autouse=True)
def reset_rate_limit():
    from uavert.api.ratelimit import limiter

    limiter._hits.clear()


@pytest.fixture(scope="session")
async def seeded(test_pool):
    now = datetime.now(UTC)
    async with test_pool.acquire() as c:
        for t in ("cell_scores", "neighbourhood_scores", "neighbourhood_crime_years", "cells", "neighbourhoods", "aqhi_readings", "official_alerts",
                  "news_events", "activity_by_hour", "cool_spaces", "crowd_events", "venues"):
            await c.execute(f"DELETE FROM {t}")
        region_id = await ensure_reference_rows(c)
        await c.execute("UPDATE sources SET data_as_of = '2026-06-30', last_collected_at = $1, last_status = 'ok'", now)
        ids = {}
        for ext, (name, lon, lat, _) in SQUARES.items():
            ids[ext] = await c.fetchval(
                "INSERT INTO neighbourhoods (region_id, external_id, name, population, valid_year, counts, geom)"
                " VALUES ($1, $2, $3, 10000, 2025, '{}', ST_GeomFromText($4, 4326)) RETURNING id",
                region_id, ext, name, square(lon, lat))
        await build_cells(c, region_id)
        for ext, (name, *_, crime) in SQUARES.items():
            reason = {"category": "crime", "text": f"{name} crime reason", "source_key": "tps_mci", "value": 3,
                      "as_of": "2025", "collected_at": now.isoformat()}
            await c.execute(
                "INSERT INTO neighbourhood_scores (neighbourhood_id, weighted_rate, crime_score, reasons, details, sources_used)"
                " VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, '{}')", ids[ext], crime * 10.0, crime, json.dumps([reason]),
                json.dumps({"groups": {}} | ({"odds": T1_ODDS, "trend": T1_TREND} if ext == "T1" else {})))
            await c.execute(
                "INSERT INTO cell_scores (h3, incident_count, own_value, local_value, smoothed_value, crime_score, reasons,"
                " sources_used, foot_traffic_per_hour, foot_traffic_counts_used, foot_traffic_first_date,"
                " foot_traffic_last_date, per_person_value, vs_surroundings, busy_area, crime_score_by_hour,"
                " intensity_by_hour)"
                " SELECT h3, 7, 1, 1, 1, $2, $3::jsonb, '{}', 500, 3, '2022-05-01', '2025-05-01', 0.01, $4, true, $5, $6"
                " FROM cells WHERE neighbourhood_id = $1",
                ids[ext], crime, json.dumps([reason | {"text": f"{name} street reason"}]), STANDS_OUT.get(ext),
                [min(100, crime + 15) if h in (1, 2, 3) else crime for h in range(24)],  # higher in the small hours
                [1.5 if h in (1, 2, 3) else 0.9 for h in range(24)])
        for h in range(24):
            await c.execute(
                "INSERT INTO activity_by_hour (hour, bikeshare_factor, factor_used, basis, retrieved_on)"
                " VALUES ($1, $2, $2, $3, '2026-10-01') ON CONFLICT (hour) DO UPDATE SET factor_used = $2, basis = $3",
                h, 0.11 if h == 2 else 1.0, "measured" if 6 <= h <= 19 else "estimated")
        await c.execute(
            "INSERT INTO aqhi_readings (station_id, station_name, region_id, geom, observed_at, aqhi)"
            " VALUES ('TST', 'Test Station', $1, ST_SetSRID(ST_MakePoint(-79.38, 43.655), 4326), $2, 3)",
            region_id, now - timedelta(minutes=30))
        lon, lat = SQUARES["T3"][1:3]
        await c.execute(
            "INSERT INTO official_alerts (region_id, source_key, external_id, alert_type, name, risk_colour, status,"
            " issued_at, expires_at, geom) VALUES ($1, 'eccc_alerts', 'TEST-WARN', 'warning', 'test heat warning',"
            " 'red', 'issued', $2, $3, ST_Multi(ST_GeomFromText($4, 4326)))",
            region_id, now - timedelta(hours=1), now + timedelta(hours=6), square(lon - 0.0001, lat - 0.0001, SIZE + 0.0002))
        every_day = json.dumps({d: ["0900", "2030"] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")})
        never = json.dumps({d: None for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")})
        for loc_id, name, hours, lon_, lat_ in (("T-LIB", "Test Library", every_day, -79.364, 43.655),
                                                ("T-CLOSED", "Test Closed Pool", never, -79.3651, 43.6551)):
            await c.execute(
                "INSERT INTO cool_spaces (location_id, region_id, name, kind, hours, geom)"
                " VALUES ($1, $2, $3, 'Cooling Location', $4::jsonb, ST_SetSRID(ST_MakePoint($5, $6), 4326))",
                loc_id, region_id, name, hours, lon_, lat_)
        toronto_today = now.astimezone(ZoneInfo("America/Toronto")).date()
        await c.execute(
            "INSERT INTO crowd_events (event_key, event_date, region_id, name, pattern, location, geom)"
            " VALUES ('T-EVENT', $1, $2, 'Test Festival', 'test', 'Test Centre', ST_SetSRID(ST_MakePoint(-79.385, 43.655), 4326))",
            toronto_today, region_id)
        await c.execute(
            "INSERT INTO venues (name, region_id, address, capacity, source_url, geom)"
            " VALUES ('Test Stadium', $1, '1 Test Way', 40000, 'https://example.test', ST_SetSRID(ST_MakePoint(-79.375, 43.655), 4326))",
            region_id)
    return ids


class FakeRouter:
    def __init__(self, result):
        self.result = result

    async def walk(self, start, end):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def router():
    """Replace the walking-route service: router(Route(...)) or router(SomeException(...))."""
    from uavert.api.app import app

    def use(result):
        app.state.router = FakeRouter(result)
    yield use
    app.state.router = None
