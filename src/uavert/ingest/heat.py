"""Extreme heat: City of Toronto Heat Relief Network (cool spaces and their hours)."""

import json

import asyncpg
import httpx

from uavert.ingest.runs import ingest_run
from uavert.sources import toronto_open_data as tod


async def store(conn: asyncpg.Connection, region_id: int, spaces: list[tod.CoolSpaceRecord]) -> int:
    async with conn.transaction():
        for s in spaces:
            await conn.execute(
                "INSERT INTO cool_spaces (location_id, region_id, name, kind, address, hours, notes, geom)"
                " VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, ST_SetSRID(ST_MakePoint($8, $9), 4326))"
                " ON CONFLICT (location_id) DO UPDATE SET name = $3, kind = $4, address = $5, hours = $6::jsonb,"
                " notes = $7, geom = EXCLUDED.geom, last_seen_at = now()",
                s.location_id, region_id, s.name, s.kind, s.address, json.dumps(s.hours), s.notes, s.lon, s.lat,
            )
        # A place the City removed from the network is no longer offered as somewhere to cool down.
        await conn.execute("DELETE FROM cool_spaces WHERE NOT (location_id = ANY($1::text[]))",
                           [s.location_id for s in spaces])
    return len(spaces)


async def run(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> None:
    async with ingest_run(conn, "toronto_cool_spaces") as r:
        spaces = await tod.fetch_cool_spaces(client)
        if not spaces:
            raise ValueError("The Heat Relief Network file had no usable places; keeping the stored list")
        r.rows_written = await store(conn, region_id, spaces)
        print(f"    toronto_cool_spaces: {len(spaces)} cool spaces")
