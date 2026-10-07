"""Criterion 48 through the API: the seeded "test heat warning" (red) covers Test Warning (T3) only."""

import pytest

pytestmark = pytest.mark.db
IN_T3 = {"lat": 43.655, "lon": -79.365}
IN_T1 = {"lat": 43.655, "lon": -79.385}


def texts(d):
    return [r["text"] for r in d["street"]["reasons"]]


async def test_heat_alert_names_the_nearest_open_cool_space(client, seeded):
    d = (await client.get("/api/v1/risk-scores", params=IN_T3 | {"hour": 12})).json()["data"]
    heat = [t for t in texts(d) if "Nearest cool space" in t]
    assert heat and "Test Library" in heat[0] and "open until 8:30 pm" in heat[0]
    assert "Test Closed Pool" not in heat[0]


async def test_late_at_night_nothing_is_open(client, seeded):
    d = (await client.get("/api/v1/risk-scores", params=IN_T3 | {"hour": 23})).json()["data"]
    assert any("No City cool space within 3 km is open at this time" in t for t in texts(d))


async def test_no_heat_alert_no_cool_space_reason(client, seeded):
    d = (await client.get("/api/v1/risk-scores", params=IN_T1 | {"hour": 12})).json()["data"]
    assert not any("cool space" in t.lower() for t in texts(d))
