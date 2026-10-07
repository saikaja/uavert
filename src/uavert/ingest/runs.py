"""Bookkeeping shared by every ingestion: sources rows, the ingest_runs history, the region."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

import asyncpg

from uavert.ingest.registry import SOURCES

TORONTO = {"code": "CA-ON-TOR", "name": "Toronto", "country": "CA", "timezone": "America/Toronto"}


@dataclass
class RunState:
    rows_written: int = 0
    data_as_of: datetime | None = None


async def ensure_reference_rows(conn: asyncpg.Connection) -> int:
    """Upsert the region and the sources list. Returns the Toronto region id."""
    for s in SOURCES:
        await conn.execute(
            "INSERT INTO sources (key, name, url, licence, attribution) VALUES ($1, $2, $3, $4, $5)"
            " ON CONFLICT (key) DO UPDATE SET name = $2, url = $3, licence = $4, attribution = $5",
            s.key, s.name, s.url, s.licence, s.attribution,
        )
    return await conn.fetchval(
        "INSERT INTO regions (code, name, country, timezone) VALUES ($1, $2, $3, $4)"
        " ON CONFLICT (code) DO UPDATE SET name = $2 RETURNING id",
        TORONTO["code"], TORONTO["name"], TORONTO["country"], TORONTO["timezone"],
    )


@asynccontextmanager
async def ingest_run(conn: asyncpg.Connection, source_key: str):
    """Record one collection run. On failure the run and the source are marked failed and the
    error is re-raised; data already stored for the source is left untouched."""
    run_id = await conn.fetchval(
        "INSERT INTO ingest_runs (source_key, started_at, status) VALUES ($1, now(), 'running') RETURNING id",
        source_key,
    )
    state = RunState()
    try:
        yield state
    except Exception as e:
        message = f"{type(e).__name__}: {e}"[:1000]
        await conn.execute(
            "UPDATE ingest_runs SET finished_at = now(), status = 'failed', error = $2 WHERE id = $1", run_id, message
        )
        await conn.execute(
            "UPDATE sources SET last_status = 'failed', last_error = $2 WHERE key = $1", source_key, message
        )
        raise
    await conn.execute(
        "UPDATE ingest_runs SET finished_at = now(), status = 'ok', rows_written = $2, data_as_of = $3 WHERE id = $1",
        run_id, state.rows_written, state.data_as_of,
    )
    await conn.execute(
        "UPDATE sources SET last_status = 'ok', last_error = NULL, last_collected_at = now(),"
        " data_as_of = COALESCE($2, data_as_of) WHERE key = $1",
        source_key, state.data_as_of,
    )
