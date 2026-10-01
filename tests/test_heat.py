"""Criteria 47-48: cool spaces and the nearest-open reason during heat alerts."""

from datetime import datetime
from pathlib import Path

from uavert.scoring import heat
from uavert.sources.toronto_open_data import parse_cool_spaces

FIX = Path(__file__).parent / "fixtures" / "heat" / "cool_spaces_sample.csv"
MONDAY_NOON = datetime(2026, 10, 5, 12, 0)
MONDAY_LATE = datetime(2026, 10, 5, 22, 0)


def test_parse_real_rows_with_hours_call_and_none():
    spaces = parse_cool_spaces(FIX.read_text(encoding="utf-8"))
    assert len(spaces) == 5
    assert spaces[0].hours["mon"] == ["0900", "2030"]
    assert any(s.hours["mon"] == "call" for s in spaces)
    assert any(s.hours["mon"] is None for s in spaces)
    assert all(-80 < s.lon < -79 and 43 < s.lat < 44 for s in spaces)


def test_open_status():
    hours = {"mon": ["0900", "2030"], "tue": "call", "wed": None}
    assert heat.open_status(hours, MONDAY_NOON) == ("open", "20:30")
    assert heat.open_status(hours, MONDAY_LATE) == ("closed", None)
    assert heat.open_status(hours, datetime(2026, 10, 6, 12)) == ("call", None)
    assert heat.open_status(hours, datetime(2026, 10, 7, 12)) == ("closed", None)


def space(name, lon, lat, mon):
    return heat.CoolSpace(name, "Cooling Location", lon, lat, {"mon": mon})


def test_nearest_open_prefers_an_open_place_and_skips_closed_ones():
    near_closed = space("Near (closed)", -79.3841, 43.6537, None)
    open_further = space("Library", -79.3900, 43.6560, ["0900", "2030"])
    call_nearer = space("Pool", -79.3850, 43.6540, "call")
    found, d, note = heat.nearest_open([near_closed, open_further, call_nearer], -79.3840, 43.6536, MONDAY_NOON)
    assert found.name == "Library" and note == "open until 8:30 pm" and 300 < d < 700
    # late at night only the "call to confirm" place is left
    found, _, note = heat.nearest_open([near_closed, open_further, call_nearer], -79.3840, 43.6536, MONDAY_LATE)
    assert found.name == "Pool" and note == "call to confirm hours"


def test_heat_reason_text():
    r = heat.heat_reason("heat warning", [space("Metro Hall", -79.3880, 43.6460, ["0800", "1900"])],
                         -79.3870, 43.6450, MONDAY_NOON, None)
    assert r.category == "alert" and r.source_key == "toronto_cool_spaces"
    assert r.text.startswith("Environment Canada heat warning in effect. Nearest cool space: Metro Hall (cooling location), about")
    assert r.text.endswith("open until 7 pm")
    none = heat.heat_reason("heat warning", [], -79.3870, 43.6450, MONDAY_NOON, None)
    assert "No City cool space within 3 km is open at this time" in none.text


def test_only_heat_alerts_count():
    assert heat.is_heat_alert("heat warning") and heat.is_heat_alert("Extreme Heat Advisory")
    assert not heat.is_heat_alert("fog advisory")
