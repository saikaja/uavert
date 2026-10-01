import pytest

from uavert.sources.routing import Route

WALK_WEST_TO_EAST = Route([(-79.388, 43.655), (-79.376, 43.655)], 1000, 720)

pytestmark = pytest.mark.db


async def test_without_hour_responses_are_all_day(client, seeded):
    d = (await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.385})).json()["data"]
    assert d["time"]["hour"] is None and d["time"]["label"] == "All day"
    assert d["street"]["score"] == 80 and not d["street"]["reasons"][0]["text"].startswith("At ")


async def test_hour_changes_street_score_and_explains_it(client, seeded):
    d = (await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.385, "hour": 2})).json()["data"]
    assert d["time"] == {"hour": 2, "label": "2 am", "window": "1 am-4 am",
                         "note": "Air quality, alerts and news show current conditions."}
    street = d["street"]
    assert street["score"] == 95 and street["categories"]["crime"] == 95
    reason = street["reasons"][0]
    assert reason["text"] == ("At 2 am: incidents near here run at about 1.5× this block's average, and about 11% "
                              "of daytime foot traffic is out (estimated from Bike Share trips)")
    assert reason["source_key"] == "activity_profile" and "collected_at" in reason
    assert d["neighbourhood"]["score"] == 80  # neighbourhood colours stay all-day


async def test_daytime_hour_says_measured(client, seeded):
    d = (await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.385, "hour": 14})).json()["data"]
    assert d["street"]["score"] == 80 and "(City pedestrian counts)" in d["street"]["reasons"][0]["text"]


async def test_cells_and_route_at_an_hour(client, seeded, router):
    cells = (await client.get("/api/v1/cells", params={"bbox": "-79.392,43.648,-79.378,43.662", "hour": 2})).json()["data"]
    assert cells["time"]["label"] == "2 am"
    assert 95 in {f["properties"]["score"] for f in cells["features"]}
    router(WALK_WEST_TO_EAST)
    d = (await client.get("/api/v1/route-risks", params={"from": "43.655,-79.388", "to": "43.655,-79.376", "hour": 2})).json()["data"]
    assert d["score"] == 95 and d["time"]["hour"] == 2


@pytest.mark.parametrize("hour", [24, -1, "late"])
async def test_bad_hour_is_422(client, seeded, hour):
    r = await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.385, "hour": hour})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
