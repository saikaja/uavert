"""Seed the Neon test branch with a tiny known dataset: 3 square neighbourhoods downtown,
their H3 cells, stored crime scores, one AQHI reading and one warning covering T3 only."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from uavert.ingest.reference import build_cells
from uavert.ingest.runs import ensure_reference_rows

SQUARES = {  # external_id: (name, min_lon, min_lat, crime_score)
    "T1": ("Test Centre", -79.390, 43.650, 80),
    "T2": ("Test East", -79.380, 43.650, 20),
    "T3": ("Test Warning", -79.370, 43.650, 10),
}
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
        for t in ("cell_scores", "neighbourhood_scores", "cells", "neighbourhoods", "aqhi_readings", "official_alerts",
                  "news_events", "activity_by_hour"):
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
                " VALUES ($1, $2, $3, $4::jsonb, '{\"groups\": {}}', '{}')", ids[ext], crime * 10.0, crime, json.dumps([reason]))
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
            " 'yellow', 'issued', $2, $3, ST_Multi(ST_GeomFromText($4, 4326)))",
            region_id, now - timedelta(hours=1), now + timedelta(hours=6), square(lon - 0.0001, lat - 0.0001, SIZE + 0.0002))
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
