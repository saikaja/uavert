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
    assert d["neighbourhood"]["score"] == 95  # the neighbourhood follows the hour too (01-03-time-map.md)


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


# ---- Neighbourhoods by hour (01-03-time-map.md, criteria 29 and 32) ----

async def test_neighbourhoods_without_hour_are_all_day(client, seeded):
    body = (await client.get("/api/v1/neighbourhoods")).json()["data"]
    assert body["time"]["label"] == "All day"
    assert {f["properties"]["name"]: f["properties"]["categories"]["crime"] for f in body["features"]} ==         {"Test Centre": 80, "Test East": 20, "Test Warning": 10}
    d = (await client.get(f"/api/v1/neighbourhoods/{seeded['T1']}")).json()["data"]
    assert d["score"] == 80 and d["time"]["hour"] is None and not d["reasons"][0]["text"].startswith("At ")


async def test_neighbourhood_colours_follow_the_hour(client, seeded):
    body = (await client.get("/api/v1/neighbourhoods", params={"hour": 2})).json()["data"]
    assert body["time"]["label"] == "2 am"
    crime = {f["properties"]["name"]: f["properties"]["categories"]["crime"] for f in body["features"]}
    assert crime == {"Test Centre": 95, "Test East": 20, "Test Warning": 10}  # T3 has no hourly scores: all day


async def test_neighbourhood_detail_at_an_hour_explains_the_change(client, seeded):
    d = (await client.get(f"/api/v1/neighbourhoods/{seeded['T1']}", params={"hour": 2})).json()["data"]
    assert d["score"] == 95 and d["time"]["label"] == "2 am"
    reason = next(r for r in d["reasons"] if r["category"] == "crime")
    assert reason["text"] == ("At 2 am: street blocks here typically score about 15 points higher than all day, and "
                              "about 11% of daytime foot traffic is out (estimated from Bike Share trips)")
    assert reason["source_key"] == "activity_profile" and reason["value"] == 15 and "collected_at" in reason
    assert d["odds"] and d["trend"]  # yearly figures, unchanged by the hour


async def test_neighbourhood_lower_and_unchanged_hours(client, seeded):
    morning = (await client.get(f"/api/v1/neighbourhoods/{seeded['T1']}", params={"hour": 8})).json()["data"]
    crime_reason = lambda d: next(r for r in d["reasons"] if r["category"] == "crime")["text"]
    assert morning["categories"]["crime"] == 68
    assert crime_reason(morning).startswith("At 8 am: street blocks here typically score about 12 points lower than all day, and foot traffic is about 1.0×")
    same = (await client.get(f"/api/v1/neighbourhoods/{seeded['T1']}", params={"hour": 14})).json()["data"]
    assert crime_reason(same).startswith("At 2 pm: street blocks here typically score about the same as all day")


@pytest.mark.parametrize("hour", [24, -1, "late"])
async def test_bad_hour_on_neighbourhoods_is_422(client, seeded, hour):
    for path in ("/api/v1/neighbourhoods", f"/api/v1/neighbourhoods/{seeded['T1']}"):
        r = await client.get(path, params={"hour": hour})
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
