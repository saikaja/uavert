"""Foot traffic: City of Toronto intersection counts."""

from datetime import UTC, datetime

import asyncpg
import httpx

from uavert.ingest.runs import ingest_run
from uavert.sources import toronto_open_data as tod

_COLUMNS = ["location_key", "location_name", "count_id", "count_date", "hours", "pedestrians", "bikes", "vehicles", "lon", "lat"]


async def store(conn: asyncpg.Connection, region_id: int, counts: list[tod.TrafficCount]) -> int:
    async with conn.transaction():
        await conn.execute(
            "CREATE TEMP TABLE traffic_load (location_key text, location_name text, count_id text, count_date date,"
            " hours numeric, pedestrians int, bikes int, vehicles int, lon float8, lat float8) ON COMMIT DROP"
        )
        await conn.copy_records_to_table("traffic_load", columns=_COLUMNS, records=[
            (c.location_key, c.location_name, c.count_id, c.count_date, c.hours, c.pedestrians, c.bikes, c.vehicles,
             c.lon, c.lat) for c in counts])
        result = await conn.execute(
            "INSERT INTO foot_traffic_counts (location_key, region_id, location_name, count_id, count_date, hours,"
            " pedestrians, bikes, vehicles, geom, h3)"
            " SELECT location_key, $1, location_name, count_id, count_date, hours, pedestrians, bikes, vehicles,"
            " ST_SetSRID(ST_MakePoint(lon, lat), 4326), h3_lat_lng_to_cell(point(lon, lat), 9) FROM traffic_load"
            " ON CONFLICT (location_key) DO UPDATE SET location_name = EXCLUDED.location_name,"
            " count_id = EXCLUDED.count_id, count_date = EXCLUDED.count_date, hours = EXCLUDED.hours,"
            " pedestrians = EXCLUDED.pedestrians, bikes = EXCLUDED.bikes, vehicles = EXCLUDED.vehicles,"
            " geom = EXCLUDED.geom, h3 = EXCLUDED.h3, last_seen_at = now()",
            region_id,
        )
    return int(result.split()[-1])


async def run(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> None:
    async with ingest_run(conn, "toronto_tmc") as r:
        counts = await tod.fetch_tmc(client)
        r.rows_written = await store(conn, region_id, counts)
        newest = max((c.count_date for c in counts), default=None)
        r.data_as_of = datetime(newest.year, newest.month, newest.day, tzinfo=UTC) if newest else None
        print(f"    toronto_tmc: {len(counts)} intersection counts, newest {newest}")
