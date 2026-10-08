import time

import pytest

from uavert.api.app import app
from uavert.api.ratelimit import RateLimiter
from uavert.sources.geocode import Place, parse_latlon
from uavert.sources.http import SourceUnavailable

pytestmark = pytest.mark.db


class FakeGeocoder:
    PLACES = {
        "1 test centre st": Place("1 Test Centre St, Toronto", -79.385, 43.655),
        "100 main st, mississauga": Place("100 Main St, Mississauga", -79.64, 43.59),
    }

    def __init__(self, down=False):
        self.down = down

    async def search(self, query):
        if self.down:
            raise SourceUnavailable("nominatim down")
        return self.PLACES.get(query.lower())


@pytest.fixture
def geocoder():
    app.state.geocoder = FakeGeocoder()
    yield app.state.geocoder
    app.state.geocoder = None


async def test_address_returns_street_and_neighbourhood_scores(client, seeded, geocoder):
    t = time.perf_counter()
    r = await client.get("/api/v1/risk-scores", params={"address": "1 Test Centre St"})
    assert time.perf_counter() - t < 2
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["location"]["display_name"] == "1 Test Centre St, Toronto"
    assert d["neighbourhood"]["name"] == "Test Centre" and d["neighbourhood"]["score"] == 80
    assert d["street"]["h3"] and d["street"]["score"] == 80 and d["street"]["band"] == "high"
    assert d["street"]["reasons"][0]["text"] == "Test Centre street reason"
    s = d["street"]
    assert (s["foot_traffic_per_hour"], s["foot_traffic_counts_used"], s["vs_surroundings"], s["busy_area"]) == (500, 3, 2.5, True)
    assert s["foot_traffic_dates"] == ["2022-05-01", "2025-05-01"]


async def test_address_carries_its_neighbourhoods_odds(client, seeded, geocoder):
    d = (await client.get("/api/v1/risk-scores", params={"address": "1 Test Centre St"})).json()["data"]
    odds = d["neighbourhood"]["odds"]
    assert (odds["year"], odds["population"], odds["toronto_population"]) == (2025, 10_000, 30_000)
    assert {k: (v["one_in"], v["toronto_one_in"]) for k, v in odds["levels"].items()} == {
        "high": (500, 500), "medium": (200, 200), "low": (77, 77), "any": (50, 50)}
    assert d["street"]["score"] == 80 and d["neighbourhood"]["score"] == 80  # scores unchanged


async def test_address_carries_its_neighbourhoods_trend(client, seeded, geocoder):
    d = (await client.get("/api/v1/risk-scores", params={"address": "1 Test Centre St"})).json()["data"]
    trend = d["neighbourhood"]["trend"]
    assert trend["windows"]["5"]["groups"]["violent"]["change_pct"] == 31
    assert d["neighbourhood"]["odds"]["year"] == 2025 and d["neighbourhood"]["score"] == 80  # odds and score unchanged


async def test_neighbourhood_without_stored_odds_returns_null(client, seeded):
    r = await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.365})
    assert r.json()["data"]["neighbourhood"]["odds"] is None


async def test_lat_lon_instead_of_address(client, seeded):
    r = await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.365})
    assert r.status_code == 200 and r.json()["data"]["neighbourhood"]["name"] == "Test Warning"


@pytest.mark.parametrize("params,status,code", [
    ({"address": "nowhere at all"}, 404, "address_not_found"),
    ({"address": "100 Main St, Mississauga"}, 422, "outside_coverage"),
    ({}, 422, "validation_error"),
    ({"address": "x"}, 422, "validation_error"),
])
async def test_destination_errors(client, seeded, geocoder, params, status, code):
    r = await client.get("/api/v1/risk-scores", params=params)
    assert r.status_code == status and r.json()["error"]["code"] == code
    assert r.json()["error"]["message"]


async def test_geocoder_down_is_502(client, seeded, geocoder):
    geocoder.down = True
    r = await client.get("/api/v1/risk-scores", params={"address": "1 Test Centre St"})
    assert r.status_code == 502 and r.json()["error"]["code"] == "upstream_unavailable"


def test_rate_limiter_window():
    lim = RateLimiter(per_minute=2)
    assert lim.allow("ip", 0) and lim.allow("ip", 1) and not lim.allow("ip", 2)
    assert lim.allow("ip", 61)  # first hit has left the window
    assert lim.allow("other", 2)


def test_parse_latlon():
    assert parse_latlon(" 43.65, -79.38 ") == Place("43.65000, -79.38000", -79.38, 43.65)
    assert parse_latlon("Queen St W") is None and parse_latlon("95,-79") is None


async def test_map_clicks_by_coordinates_are_not_rate_limited(client, seeded):
    # Found in the phase 5 review: lat/lon lookups call no outside service, so they don't count toward the limit.
    statuses = {(await client.get("/api/v1/risk-scores", params={"lat": 43.655, "lon": -79.385})).status_code
                for _ in range(35)}
    assert statuses == {200}
