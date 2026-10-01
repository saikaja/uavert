import time

import pytest

from uavert.sources.http import SourceUnavailable
from uavert.sources.routing import NoRoute, Route

pytestmark = pytest.mark.db

# Seeded squares: Test Centre (crime 80) west, Test East (20), Test Warning (10 + warning -> 90) east.
WEST, EAST = "43.655,-79.388", "43.655,-79.376"
WALK_WEST_TO_EAST = Route([(-79.388, 43.655), (-79.376, 43.655)], 1000, 720)


async def test_route_score_is_highest_along_route_with_riskiest_stretches(client, seeded, router):
    router(WALK_WEST_TO_EAST)
    t = time.perf_counter()
    r = await client.get("/api/v1/route-risks", params={"from": WEST, "to": EAST})
    assert time.perf_counter() - t < 3
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["distance_m"] == 1000 and d["geometry"]["type"] == "LineString"
    assert d["score"] == 80 and d["band"] == "high"  # Test Centre's crime 80 is the highest along the way
    segs = d["riskiest_segments"]
    assert len(segs) == 1 and d["segments_note"] is None  # only Test Centre cells stand out (2.5x)
    assert segs[0]["vs_surroundings"] == 2.5 and segs[0]["score"] == 80 and segs[0]["foot_traffic_per_hour"] == 500
    assert segs[0]["reasons"][0]["text"] == "Test Centre street reason"
    assert segs[0]["geometry"]["type"] == "LineString" and segs[0]["length_m"] > 0


async def test_route_where_nothing_stands_out_says_so(client, seeded, router):
    router(Route([(-79.378, 43.655), (-79.372, 43.655)], 500, 360))  # inside Test East only (1.0x)
    d = (await client.get("/api/v1/route-risks", params={"from": "43.655,-79.378", "to": "43.655,-79.372"})).json()["data"]
    assert d["riskiest_segments"] == [] and d["segments_note"] == "No stretch of this walk stands out from its surroundings."


async def test_same_start_and_end_scores_the_place(client, seeded, router):
    router(WALK_WEST_TO_EAST)
    d = (await client.get("/api/v1/route-risks", params={"from": WEST, "to": WEST})).json()["data"]
    assert d["distance_m"] == 0 and d["score"] == 80 and d["riskiest_segments"] == []


@pytest.mark.parametrize("result,status,code", [
    (NoRoute("none"), 422, "no_route"),
    (SourceUnavailable("down"), 502, "upstream_unavailable"),
    (Route([(-79.388, 43.655), (-79.376, 43.655)], 12_500, 9000), 422, "route_too_long"),
])
async def test_route_errors(client, seeded, router, result, status, code):
    router(result)
    r = await client.get("/api/v1/route-risks", params={"from": WEST, "to": EAST})
    assert r.status_code == status and r.json()["error"]["code"] == code


async def test_route_outside_toronto_or_too_far_apart(client, seeded, router):
    router(WALK_WEST_TO_EAST)
    r = await client.get("/api/v1/route-risks", params={"from": WEST, "to": "43.59,-79.64"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "outside_coverage"


async def test_route_needs_both_ends(client, seeded):
    r = await client.get("/api/v1/route-risks", params={"from": WEST})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
