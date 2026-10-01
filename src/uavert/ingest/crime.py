"""Crime incidents from Toronto Police: Major Crime Indicators, shootings and homicides."""

import asyncpg
import httpx

from uavert.ingest.reference import load_offence_map
from uavert.ingest.runs import ingest_run
from uavert.sources import arcgis, tps

START_DATE = "2025-01-01"  # covers calendar 2025 (neighbourhood scores) and the last 12 months (street scores)
INCIDENT_SOURCES = ("tps_mci", "tps_shootings", "tps_homicides")

_LOAD_COLUMNS = ["source_key", "event_id", "ucr_code", "ucr_ext", "offence", "csi_offence_key",
                 "premises_type", "occurred_at", "hood_external_id", "lon", "lat"]


async def fetch(client: httpx.AsyncClient, source_key: str) -> list[tps.Incident]:
    where = f"OCC_DATE >= DATE '{START_DATE}'"
    out = []
    async for page in arcgis.query_pages(client, tps.LAYERS[source_key], where, tps.INCIDENT_FIELDS[source_key]):
        out += [tps.parse_incident(source_key, f["attributes"]) for f in page]
    return out


async def store(conn: asyncpg.Connection, region_id: int, incidents: list[tps.Incident]) -> int:
    """Insert or update incidents by (source, event, offence). Re-runs refresh last_seen_at and keep collected_at."""
    offence_map = load_offence_map()
    offence_map.check({(i.source_key, i.ucr_code, i.ucr_ext, i.offence) for i in incidents})
    records = [
        (i.source_key, i.event_id, i.ucr_code, i.ucr_ext, i.offence,
         offence_map.resolve(i.source_key, i.ucr_code, i.ucr_ext).csi_offence_key,
         i.premises_type, i.occurred_at, i.hood_external_id, i.lon, i.lat)
        for i in incidents
    ]
    async with conn.transaction():
        await conn.execute(
            "CREATE TEMP TABLE incidents_load (source_key text, event_id text, ucr_code text, ucr_ext text,"
            " offence text, csi_offence_key text, premises_type text, occurred_at timestamptz,"
            " hood_external_id text, lon double precision, lat double precision) ON COMMIT DROP"
        )
        await conn.copy_records_to_table("incidents_load", records=records, columns=_LOAD_COLUMNS)
        # One row per unique key: a source can list the same offence once per victim.
        result = await conn.execute(
            """
            INSERT INTO incidents (region_id, source_key, event_id, ucr_code, ucr_ext, offence, csi_offence_key,
                                   premises_type, occurred_at, hood_external_id, geom, h3)
            SELECT DISTINCT ON (source_key, event_id, ucr_code, ucr_ext)
                   $1, source_key, event_id, ucr_code, ucr_ext, offence, csi_offence_key, premises_type,
                   occurred_at, hood_external_id,
                   CASE WHEN lon IS NOT NULL THEN ST_SetSRID(ST_MakePoint(lon, lat), 4326) END,
                   CASE WHEN lon IS NOT NULL THEN h3_lat_lng_to_cell(point(lon, lat), 9) END
            FROM incidents_load
            ORDER BY source_key, event_id, ucr_code, ucr_ext, occurred_at
            ON CONFLICT (source_key, event_id, ucr_code, ucr_ext) DO UPDATE SET
                offence = EXCLUDED.offence, csi_offence_key = EXCLUDED.csi_offence_key,
                premises_type = EXCLUDED.premises_type, occurred_at = EXCLUDED.occurred_at,
                hood_external_id = EXCLUDED.hood_external_id, geom = EXCLUDED.geom, h3 = EXCLUDED.h3,
                last_seen_at = now()
            """,
            region_id,
        )
    return int(result.split()[-1])


async def run(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> None:
    for source_key in INCIDENT_SOURCES:
        async with ingest_run(conn, source_key) as r:
            incidents = await fetch(client, source_key)
            r.rows_written = await store(conn, region_id, incidents)
            r.data_as_of = max((i.occurred_at for i in incidents), default=None)
            latest = f"{r.data_as_of:%Y-%m-%d}" if r.data_as_of else "none"
            print(f"    {source_key}: {len(incidents)} records fetched, {r.rows_written} stored, latest {latest}")
