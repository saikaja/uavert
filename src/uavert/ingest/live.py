"""Live conditions: AQHI readings and weather alerts from Environment Canada."""

import json

import asyncpg
import httpx

from uavert.ingest.runs import ingest_run
from uavert.sources import eccc


async def store_aqhi(conn: asyncpg.Connection, region_id: int, readings: list[eccc.AqhiReading]) -> int:
    async with conn.transaction():
        for r in readings:
            await conn.execute(
                "INSERT INTO aqhi_readings (station_id, station_name, region_id, geom, observed_at, aqhi)"
                " VALUES ($1, $2, $3, ST_SetSRID(ST_MakePoint($4, $5), 4326), $6, $7)"
                " ON CONFLICT (station_id, observed_at) DO UPDATE SET aqhi = $7, last_seen_at = now()",
                r.station_id, r.station_name, region_id, r.lon, r.lat, r.observed_at, r.aqhi,
            )
    return len(readings)


async def store_alerts(conn: asyncpg.Connection, region_id: int, alerts: list[eccc.AlertRecord]) -> int:
    async with conn.transaction():
        for a in alerts:
            await conn.execute(
                "INSERT INTO official_alerts (region_id, source_key, external_id, alert_type, alert_code, name,"
                " risk_colour, status, issued_at, expires_at, text, geom)"
                " VALUES ($1, 'eccc_alerts', $2, $3, $4, $5, $6, $7, $8, $9, $10,"
                " ST_SetSRID(ST_GeomFromGeoJSON($11), 4326))"
                " ON CONFLICT (source_key, external_id) DO UPDATE SET alert_type = $3, alert_code = $4, name = $5,"
                " risk_colour = $6, status = $7, issued_at = $8, expires_at = $9, text = $10, geom = EXCLUDED.geom,"
                " last_seen_at = now()",
                region_id, a.external_id, a.alert_type, a.alert_code, a.name, a.risk_colour, a.status,
                a.issued_at, a.expires_at, a.text, json.dumps(a.geometry),
            )
        # The feed lists every current alert for the area; one that has dropped out was cancelled or has ended.
        await conn.execute(
            "UPDATE official_alerts SET status = 'ended' WHERE region_id = $1 AND source_key = 'eccc_alerts'"
            " AND status <> 'ended' AND NOT (external_id = ANY($2::text[]))",
            region_id, [a.external_id for a in alerts],
        )
    return len(alerts)


async def run_aqhi(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> None:
    async with ingest_run(conn, "eccc_aqhi") as r:
        readings = await eccc.fetch_aqhi(client)
        r.rows_written = await store_aqhi(conn, region_id, readings)
        r.data_as_of = max((x.observed_at for x in readings), default=None)
        print(f"    eccc_aqhi: {len(readings)} station readings")


async def run_alerts(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> None:
    async with ingest_run(conn, "eccc_alerts") as r:
        alerts = await eccc.fetch_alerts(client)
        r.rows_written = await store_alerts(conn, region_id, alerts)
        r.data_as_of = max((a.issued_at for a in alerts), default=None)
        print(f"    eccc_alerts: {len(alerts)} alerts covering the Toronto area")
