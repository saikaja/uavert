from datetime import UTC, datetime

import pytest

from uavert import db
from uavert.ingest import crime
from uavert.ingest.reference import UnmappedOffence
from uavert.ingest.runs import ensure_reference_rows
from uavert.sources.tps import Incident

pytestmark = pytest.mark.db
T = datetime(2026, 5, 1, 12, tzinfo=UTC)


def incident(event_id, code="1610", ext="100", lon=-79.3840, lat=43.6536, offence="Robbery With Weapon"):
    return Incident("tps_mci", event_id, code, ext, offence, "Outside", T, "76", lon, lat)


@pytest.fixture
async def conn_and_region(test_db_url):
    c = await db.connect(test_db_url)
    yield c, await ensure_reference_rows(c)
    await c.execute("DELETE FROM incidents WHERE event_id LIKE 'TEST-%'")
    await c.close()


async def test_rerun_adds_no_duplicates_and_keeps_collected_at(conn_and_region):
    conn, region_id = conn_and_region
    rows = [incident("TEST-1"), incident("TEST-1"), incident("TEST-2", lon=None, lat=None)]
    await crime.store(conn, region_id, rows)
    first = await conn.fetch("SELECT event_id, collected_at FROM incidents WHERE event_id LIKE 'TEST-%' ORDER BY 1")
    await crime.store(conn, region_id, rows)
    second = await conn.fetch(
        "SELECT event_id, collected_at, last_seen_at FROM incidents WHERE event_id LIKE 'TEST-%' ORDER BY 1"
    )
    assert [r["event_id"] for r in second] == ["TEST-1", "TEST-2"]
    assert [r["collected_at"] for r in second] == [r["collected_at"] for r in first]
    assert all(r["last_seen_at"] >= r["collected_at"] for r in second)


async def test_incident_without_location_is_kept_without_a_cell(conn_and_region):
    conn, region_id = conn_and_region
    await crime.store(conn, region_id, [incident("TEST-3"), incident("TEST-4", lon=None, lat=None)])
    rows = {r["event_id"]: r for r in await conn.fetch("SELECT event_id, h3::text, geom IS NULL AS no_geom, csi_offence_key FROM incidents WHERE event_id IN ('TEST-3','TEST-4')")}
    assert rows["TEST-3"]["h3"] == "892b9bc46d7ffff" and rows["TEST-3"]["csi_offence_key"] == "robbery"
    assert rows["TEST-4"]["h3"] is None and rows["TEST-4"]["no_geom"]


async def test_unmapped_offence_stops_the_load(conn_and_region):
    conn, region_id = conn_and_region
    with pytest.raises(UnmappedOffence, match="9999-100"):
        await crime.store(conn, region_id, [incident("TEST-5", code="9999", offence="Unknown")])
    assert await conn.fetchval("SELECT count(*) FROM incidents WHERE event_id = 'TEST-5'") == 0
