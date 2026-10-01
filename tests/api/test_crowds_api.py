"""Criteria 50-51 through the API: a test festival today at (-79.385, 43.655), a test stadium at (-79.375, 43.655)."""

import pytest

pytestmark = pytest.mark.db


async def test_event_today_raises_crowds_nearby(client, seeded):
    d = (await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.386})).json()["data"]["street"]
    assert d["categories"]["crowds"] == 35
    assert any(r["category"] == "crowds" and r["text"].startswith("Test Festival today") for r in d["reasons"])


async def test_venue_is_context_with_no_score(client, seeded):
    # about 1.1 km from the festival (outside its 1 km), about 320 m from the stadium (inside 500 m)
    d = (await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.371})).json()["data"]["street"]
    assert d["categories"]["crowds"] == 0
    assert {"category": "crowds", "text": "Near Test Stadium: can draw about 40,000 people on event days"}.items() <= next(
        r for r in d["reasons"] if r["category"] == "crowds").items()


async def test_crowds_category_in_cells(client, seeded):
    cells = (await client.get("/api/v1/cells", params={"bbox": "-79.392,43.648,-79.378,43.662"})).json()["data"]["features"]
    assert all("crowds" in f["properties"]["categories"] for f in cells)
    assert 35 in {f["properties"]["categories"]["crowds"] for f in cells}
