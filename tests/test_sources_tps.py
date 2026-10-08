import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from uavert.sources import arcgis, tps
from uavert.sources.http import SourceUnavailable, get_json

FIX = Path(__file__).parent / "fixtures" / "tps"


def load(name):
    return json.loads((FIX / name).read_text())


def test_parse_mci_record():
    a = load("mci_page.json")["features"][0]["attributes"]
    i = tps.parse_incident("tps_mci", a)
    assert i.event_id == "GO-20261128087"
    assert (i.ucr_code, i.ucr_ext, i.offence) == ("1420", "110", "Assault Bodily Harm")
    assert i.premises_type == "Outside"
    assert i.hood_external_id == "16"  # '016' normalised
    # OCC_DATE is local midnight (04:00 UTC in June); OCC_HOUR 0 adds nothing
    assert i.occurred_at == datetime(2026, 6, 1, 4, 0, tzinfo=UTC)
    assert i.lat == pytest.approx(43.6306, abs=1e-4) and i.lon == pytest.approx(-79.4831, abs=1e-4)


def test_parse_mci_without_location():
    a = load("mci_no_location.json")["features"][0]["attributes"]
    i = tps.parse_incident("tps_mci", a)
    assert i.lat is None and i.lon is None
    assert i.hood_external_id is None  # 'NSA'


def test_parse_shooting_and_homicide():
    s = tps.parse_incident("tps_shootings", load("shootings_page.json")["features"][0]["attributes"])
    assert (s.ucr_code, s.ucr_ext, s.offence, s.premises_type) == ("*", "*", "Firearm Discharge", None)
    assert s.occurred_at == datetime(2026, 1, 2, 7, 0, tzinfo=UTC)  # 05:00 UTC date + OCC_HOUR 2
    h = tps.parse_incident("tps_homicides", load("homicides_page.json")["features"][0]["attributes"])
    assert h.offence == "Homicide (Shooting)" and h.hood_external_id == "31"


def test_parse_neighbourhood():
    n = tps.parse_neighbourhood(load("ncr_one.geojson")["features"][0], 2025)
    assert (n.external_id, n.name, n.population) == ("95", "Annex", 38487)
    assert n.counts["ASSAULT"] == 416 and n.counts["THEFTFROMMV"] == 85
    assert n.geom.geom_type == "MultiPolygon" and n.geom.is_valid


def test_parse_crime_years():
    # 01-03-trends.md: every offence, every year 2014-2025, count and rate as published
    rows = tps.parse_crime_years(load("ncr_years_one.json")["attributes"], 2014, 2025)
    assert len(rows) == 9 * 12
    by = {(r.year, r.offence): r for r in rows}
    assert {r.hood_external_id for r in rows} == {"170"}
    assert by[(2014, "ASSAULT")].count == 387 and by[(2014, "ASSAULT")].rate_per_100k == 3750
    assert by[(2025, "ASSAULT")].count == 560


def test_parse_crime_years_refuses_a_missing_year():
    attrs = load("ncr_years_one.json")["attributes"]
    del attrs["ROBBERY_RATE_2019"]
    with pytest.raises(ValueError, match="ROBBERY_RATE_2019"):
        tps.parse_crime_years(attrs, 2014, 2025)


def test_ncr_year_fields_cover_counts_and_rates():
    fields = tps.ncr_year_fields(2014, 2025).split(",")
    assert len(fields) == 9 * 12 * 2 and "THEFTOVER_RATE_2025" in fields and "ASSAULT_2014" in fields


@respx.mock
async def test_query_pages_follows_transfer_limit():
    url = "https://example.test/layer"
    route = respx.get(f"{url}/query")
    route.side_effect = [
        httpx.Response(200, json={"features": [{"attributes": {"n": 1}}] * 2, "exceededTransferLimit": True}),
        httpx.Response(200, json={"features": [{"attributes": {"n": 2}}]}),
    ]
    async with httpx.AsyncClient() as c:
        pages = [p async for p in arcgis.query_pages(c, url, "1=1")]
    assert [len(p) for p in pages] == [2, 1]
    assert route.calls[1].request.url.params["resultOffset"] == "2"


@respx.mock
async def test_arcgis_error_body_is_source_unavailable():
    respx.get("https://example.test/layer/query").respond(200, json={"error": {"message": "Invalid query"}})
    async with httpx.AsyncClient() as c:
        with pytest.raises(SourceUnavailable, match="Invalid query"):
            [p async for p in arcgis.query_pages(c, "https://example.test/layer", "bad")]


@respx.mock
async def test_timeout_becomes_source_unavailable(monkeypatch):
    monkeypatch.setattr("uavert.sources.http.asyncio.sleep", _no_sleep)
    route = respx.get("https://example.test/x").mock(side_effect=httpx.ConnectTimeout("slow"))
    async with httpx.AsyncClient() as c:
        with pytest.raises(SourceUnavailable):
            await get_json(c, "https://example.test/x")
    assert route.call_count == 3  # first try + 2 retries


async def _no_sleep(_):
    return None
