import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import respx

from uavert import db
from uavert.ingest import live
from uavert.ingest.runs import ensure_reference_rows
from uavert.scoring import alerts as alert_rules
from uavert.scoring.combine import combine
from uavert.scoring.environment import aqhi_score, environment, health_canada_risk
from uavert.sources import eccc

FIX = Path(__file__).parent / "fixtures" / "eccc"
NOW = datetime(2026, 10, 1, 16, tzinfo=UTC)


def fixture(name):
    return json.loads((FIX / name).read_text())


def test_parse_real_aqhi_response():
    readings = [eccc.parse_aqhi(f) for f in fixture("aqhi_latest.json")["features"]]
    west = next(r for r in readings if r.station_name == "Toronto West")
    assert west.aqhi == 2.51 and west.observed_at == datetime(2026, 10, 1, 15, tzinfo=UTC)
    assert west.lon == pytest.approx(-79.56589)


def test_parse_real_warning():
    a = eccc.parse_alert(fixture("alerts_one_warning.json")["features"][0])
    assert a.alert_type == "warning" and a.name == "storm surge warning" and a.geometry["type"] == "Polygon"


@pytest.mark.parametrize("aqhi,score,band_risk", [
    (1, 0, "low"), (2.5, 15, "low"), (3.4, 24, "low"), (4, 29, "moderate"), (6.4, 49, "moderate"),
    (8, 59, "high"), (10.4, 74, "high"), (11, 78, "very high"), (20, 100, "very high"),
])
def test_aqhi_maps_onto_health_canada_bands(aqhi, score, band_risk):
    assert aqhi_score(aqhi) == score
    assert health_canada_risk(aqhi) == band_risk


def test_stale_reading_is_used_but_flagged():
    score, reasons = environment("Toronto Downtown", 2.0, NOW - timedelta(hours=7), None, NOW)
    assert score == aqhi_score(2.0)
    assert "not current, last reading 7 h ago" in reasons[0].text


def test_no_reading_scores_zero_with_reason():
    score, reasons = environment(None, None, None, None, NOW)
    assert score == 0 and reasons[0].text == "No current air quality reading"


def alert(alert_type, colour="yellow", status="issued", expires=NOW + timedelta(hours=6)):
    return alert_rules.Alert("test " + alert_type, alert_type, colour, status, NOW - timedelta(hours=1), expires)


# Criterion 8: warnings put the area in the top band; advisories don't override.
def test_warning_puts_area_in_high_band_and_names_alert():
    score, reasons = alert_rules.alert_score([alert("warning")], NOW)
    combined = combine({"crime": 10, "alert": score}, reasons)
    assert combined.band == "high" and "test warning" in combined.reasons[0].text


def test_orange_advisory_counts_as_top_band():
    assert alert_rules.alert_score([alert("advisory", colour="orange")], NOW)[0] == 90


def test_advisory_sets_moderate_floor_and_statement_informs_only():
    assert alert_rules.alert_score([alert("advisory")], NOW)[0] == 25
    score, reasons = alert_rules.alert_score([alert("statement")], NOW)
    assert score == 0 and len(reasons) == 1


def test_ended_or_expired_alerts_are_ignored():
    assert alert_rules.alert_score([alert("warning", status="ended")], NOW) == (0, [])
    assert alert_rules.alert_score([alert("warning", expires=NOW - timedelta(minutes=1))], NOW) == (0, [])


# Criterion 17: a failed fetch keeps the stored rows and is recorded as failed.
@pytest.mark.db
@respx.mock
async def test_failed_fetch_keeps_old_rows_and_records_failure(test_db_url, monkeypatch):
    monkeypatch.setattr("uavert.sources.http.asyncio.sleep", _no_sleep)
    conn = await db.connect(test_db_url)
    try:
        region_id = await ensure_reference_rows(conn)
        await live.store_aqhi(conn, region_id, [eccc.parse_aqhi(f) for f in fixture("aqhi_latest.json")["features"]])
        before = await conn.fetchval("SELECT count(*) FROM aqhi_readings")
        respx.get(url__startswith=eccc.API).mock(side_effect=httpx.ConnectTimeout("down"))
        async with httpx.AsyncClient() as client:
            with pytest.raises(Exception):
                await live.run_aqhi(conn, client, region_id)
        assert await conn.fetchval("SELECT count(*) FROM aqhi_readings") == before
        run = await conn.fetchrow("SELECT status, error FROM ingest_runs WHERE source_key = 'eccc_aqhi' ORDER BY id DESC LIMIT 1")
        assert run["status"] == "failed" and run["error"].startswith("SourceUnavailable")
        assert await conn.fetchval("SELECT last_status FROM sources WHERE key = 'eccc_aqhi'") == "failed"
    finally:
        await conn.close()


async def _no_sleep(_):
    return None


@pytest.mark.db
@respx.mock
async def test_failed_traffic_download_keeps_stored_counts(test_db_url, monkeypatch):
    from uavert.ingest import traffic
    from uavert.sources import toronto_open_data as tod

    monkeypatch.setattr("uavert.sources.http.asyncio.sleep", _no_sleep)
    conn = await db.connect(test_db_url)
    try:
        region_id = await ensure_reference_rows(conn)
        sample = tod.parse_tmc_csv((Path(__file__).parent / "fixtures" / "traffic" / "tmc_sample.csv").read_text(encoding="utf-8"))
        await traffic.store(conn, region_id, sample)
        before = await conn.fetchval("SELECT count(*) FROM foot_traffic_counts")
        assert before >= len(sample)
        respx.get(url__startswith=tod.CKAN).mock(side_effect=httpx.ConnectTimeout("down"))
        async with httpx.AsyncClient() as client:
            with pytest.raises(Exception):
                await traffic.run(conn, client, region_id)
        assert await conn.fetchval("SELECT count(*) FROM foot_traffic_counts") == before
        assert await conn.fetchval("SELECT last_status FROM sources WHERE key = 'toronto_tmc'") == "failed"
    finally:
        await conn.execute("DELETE FROM foot_traffic_counts")
        await conn.close()
