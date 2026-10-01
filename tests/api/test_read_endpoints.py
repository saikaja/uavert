import re

import pytest

pytestmark = pytest.mark.db
BANDS = {"lower", "moderate", "elevated", "high"}


async def test_neighbourhoods_geojson_with_scores(client, seeded):
    r = await client.get("/api/v1/neighbourhoods")
    assert r.status_code == 200
    body = r.json()
    feats = {f["properties"]["name"]: f["properties"] for f in body["data"]["features"]}
    assert set(feats) == {"Test Centre", "Test East", "Test Warning"}
    centre = feats["Test Centre"]
    assert centre["score"] == 80 and centre["band"] == "high"
    assert set(centre["categories"]) == {"crime", "environment", "alert", "news"}
    assert body["data"]["features"][0]["geometry"]["type"] in ("Polygon", "MultiPolygon")


async def test_warning_moves_covered_neighbourhood_to_high(client, seeded):
    feats = {f["properties"]["name"]: f["properties"] for f in (await client.get("/api/v1/neighbourhoods")).json()["data"]["features"]}
    assert feats["Test Warning"]["categories"]["alert"] == 90 and feats["Test Warning"]["band"] == "high"
    assert feats["Test East"]["categories"]["alert"] == 0
    detail = (await client.get(f"/api/v1/neighbourhoods/{seeded['T3']}")).json()["data"]
    assert "test heat warning" in detail["reasons"][0]["text"]


async def test_neighbourhood_detail_reasons_carry_source_and_dates(client, seeded):
    r = await client.get(f"/api/v1/neighbourhoods/{seeded['T1']}")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["name"] == "Test Centre" and 1 <= len(d["reasons"]) <= 3
    for reason in d["reasons"]:
        assert reason["source_key"] and "as_of" in reason and "collected_at" in reason


async def test_unknown_neighbourhood_is_404(client, seeded):
    r = await client.get("/api/v1/neighbourhoods/999999")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


async def test_meta_lists_data_date_and_collection_time_per_source(client, seeded):
    meta = (await client.get("/api/v1/neighbourhoods")).json()["meta"]
    assert meta["generated_at"]
    assert set(meta["sources"]["tps_mci"]) == {"as_of", "collected_at"}
    assert meta["sources"]["tps_mci"]["collected_at"]


async def test_cells_in_bbox(client, seeded):
    r = await client.get("/api/v1/cells", params={"bbox": "-79.395,43.645,-79.355,43.665"})
    assert r.status_code == 200
    props = [f["properties"] for f in r.json()["data"]["features"]]
    assert props and all(p["band"] in BANDS and p["incident_count"] == 7 and p["top_reason"] for p in props)


@pytest.mark.parametrize("bbox,code", [
    ("-79.6,43.6,-79.2,43.8", "bbox_too_large"),
    ("-79.36,43.66,-79.39,43.65", "invalid_bbox"),
    ("not,a,bbox", "invalid_bbox"),
])
async def test_cells_bad_bbox(client, seeded, bbox, code):
    r = await client.get("/api/v1/cells", params={"bbox": bbox})
    assert r.status_code == 422 and r.json()["error"]["code"] == code


async def test_sources_list_freshness(client, seeded):
    data = (await client.get("/api/v1/sources")).json()["data"]
    mci = next(s for s in data if s["key"] == "tps_mci")
    assert mci["licence"] and mci["attribution"] and mci["as_of"].startswith("2026-06-30") and mci["collected_at"]


async def test_scoring_rules(client, seeded):
    d = (await client.get("/api/v1/scoring-rules")).json()["data"]
    assert [b["band"] for b in d["bands"]] == ["lower", "moderate", "elevated", "high"]
    assert d["parameters"]["min_incidents_for_own_score"] == 5


# Criterion 9: no band or label anywhere says "safe".
async def test_no_response_labels_anything_safe(client, seeded):
    for path in ["/api/v1/neighbourhoods", f"/api/v1/neighbourhoods/{seeded['T1']}",
                 "/api/v1/cells?bbox=-79.395,43.645,-79.355,43.665", "/api/v1/scoring-rules"]:
        text = (await client.get(path)).text
        assert not re.search(r'"(band|label)"\s*:\s*"[^"]*safe', text, re.I), path
