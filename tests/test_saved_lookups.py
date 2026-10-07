"""Criteria 30-31: saved address and route lookups survive a restart and expire."""

import httpx
import pytest
import respx

from uavert import db
from uavert.sources.geocode import Geocoder, Place
from uavert.sources.routing import Router, route_key

pytestmark = pytest.mark.db
NOMINATIM = "https://nominatim.test"
OSRM = "https://osrm.test"
ADDRESS = "1 Saved Lookup Test St, Toronto"
A, B = Place("a", -79.38, 43.65), Place("b", -79.37, 43.66)
OSRM_OK = {"code": "Ok", "routes": [{"geometry": {"coordinates": [[-79.38, 43.65], [-79.37, 43.66]]},
                                     "distance": 1400.0, "duration": 1000.0}]}


@pytest.fixture
async def conn(test_db_url):
    c = await db.connect(test_db_url)
    await c.execute("DELETE FROM geocode_cache WHERE query_key LIKE '%saved lookup test%' OR query_key = 'nowhere saved test'")
    await c.execute("DELETE FROM route_cache WHERE route_key = $1", route_key(A, B))
    yield c
    await c.execute("DELETE FROM geocode_cache WHERE query_key LIKE '%saved lookup test%' OR query_key = 'nowhere saved test'")
    await c.execute("DELETE FROM route_cache WHERE route_key = $1", route_key(A, B))
    await c.close()


@respx.mock
async def test_address_is_reused_after_restart_without_calling_nominatim(conn):
    call = respx.get(f"{NOMINATIM}/search").respond(json=[{"display_name": "Saved St", "lon": "-79.38", "lat": "43.65"}])
    async with httpx.AsyncClient() as client:
        first = await Geocoder(client, NOMINATIM, db=conn).search(ADDRESS)
        restarted = Geocoder(client, NOMINATIM, db=conn)  # new instance: empty memory, same database
        again = await restarted.search(ADDRESS)
    assert first == again == Place("Saved St", -79.38, 43.65)
    assert call.call_count == 1
    row = await conn.fetchrow("SELECT found, collected_at FROM geocode_cache WHERE query_key = $1", " ".join(ADDRESS.lower().split()))
    assert row["found"] and row["collected_at"]


@respx.mock
async def test_not_found_is_saved_too(conn):
    call = respx.get(f"{NOMINATIM}/search").respond(json=[])
    async with httpx.AsyncClient() as client:
        assert await Geocoder(client, NOMINATIM, db=conn).search("nowhere saved test") is None
        assert await Geocoder(client, NOMINATIM, db=conn).search("nowhere saved test") is None
    assert call.call_count == 1


@respx.mock
async def test_saved_address_expires_after_30_days(conn):
    call = respx.get(f"{NOMINATIM}/search").respond(json=[{"display_name": "Saved St", "lon": "-79.38", "lat": "43.65"}])
    async with httpx.AsyncClient() as client:
        await Geocoder(client, NOMINATIM, db=conn).search(ADDRESS)
        await conn.execute("UPDATE geocode_cache SET collected_at = now() - interval '31 days' WHERE query_key = $1",
                           " ".join(ADDRESS.lower().split()))
        await Geocoder(client, NOMINATIM, db=conn).search(ADDRESS)
    assert call.call_count == 2


@respx.mock
async def test_route_is_reused_after_restart_and_expires_after_7_days(conn):
    call = respx.get(url__startswith=f"{OSRM}/route/v1/foot/").respond(json=OSRM_OK)
    async with httpx.AsyncClient() as client:
        first = await Router(client, OSRM, db=conn).walk(A, B)
        again = await Router(client, OSRM, db=conn).walk(A, B)
        assert first == again and again.distance_m == 1400.0 and call.call_count == 1
        await conn.execute("UPDATE route_cache SET collected_at = now() - interval '8 days' WHERE route_key = $1", route_key(A, B))
        await Router(client, OSRM, db=conn).walk(A, B)
    assert call.call_count == 2
