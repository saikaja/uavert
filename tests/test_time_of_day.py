from datetime import UTC, datetime

import h3
import pytest

from uavert.scoring import crime
from uavert.scoring.build import Event, cell_scores, local_hour


def test_window_wraps_past_midnight():
    assert crime.time_window(0) == (23, 0, 1) and crime.time_window(23) == (22, 23, 0)


def test_window_shares_and_untimed_incidents_spread_evenly():
    shares = crime.window_shares([22, 23, None], [1.0, 1.0, 2.0])
    # window 23 (22-0): 2 timed + 2 x 3/24 untimed = 2.25 of 4
    assert shares[23] == pytest.approx(2.25 / 4)
    # window 12 (11-13): only the untimed share
    assert shares[12] == pytest.approx(0.25 / 4)
    assert crime.window_shares([], []) == [3 / 24] * 24


def test_few_incidents_follow_the_city_pattern():
    # Criterion 23: 2 incidents can't outvote Toronto's pattern; 100 incidents mostly can.
    assert crime.lean_toward_city(1.0, 2, 0.1) == pytest.approx((2 * 1.0 + 10 * 0.1) / 12)
    assert crime.lean_toward_city(1.0, 100, 0.1) == pytest.approx((100 + 1) / 110)


def test_intensity_is_relative_to_an_average_three_hours():
    assert crime.intensity(3 / 24) == 1.0 and crime.intensity(6 / 24) == 2.0


def test_fewer_people_out_means_higher_risk_per_person():
    # Criterion 22: same incidents, 1,000 people an hour by day vs 10% of that at night (below the floor of 100).
    day = crime.per_person_at_hour(1000, 1.0, 1000, 1.0)
    night = crime.per_person_at_hour(1000, 1.0, 1000, 0.1)
    assert day == 1.0 and night == 10.0


def ev(i, hour, cell, source="tps_mci"):
    t = datetime(2026, 6, 20, hour + 4, tzinfo=UTC)  # Toronto is UTC-4 in June
    return Event(f"E{i}", source, "robbery", 583, "robberies", "Outside", t, "1", cell)


def test_local_hour_and_homicides_without_time():
    cell = h3.latlng_to_cell(43.6536, -79.3840, 9)
    assert local_hour(ev(1, 2, cell)) == 2
    assert local_hour(ev(2, 2, cell, source="tps_homicides")) is None  # Criterion 24


def test_hourly_scores_rise_when_streets_empty():
    a = h3.latlng_to_cell(43.6536, -79.3840, 9)
    b = h3.latlng_to_cell(43.70, -79.40, 9)
    events = [ev(i, h, a) for i, h in enumerate([1, 2, 3, 13, 14, 15] * 3)] + [ev(100 + i, 14, b) for i in range(3)]
    activity = [0.1] * 6 + [1.0] * 14 + [0.5] * 4  # few people out from midnight to 6 am
    traffic = [(a, 1000.0, datetime(2025, 5, 1).date())]
    out = cell_scores(events, {a: 1, b: 1}, {1: "Test"}, {}, traffic, activity)
    by_hour = out[a]["crime_score_by_hour"]
    assert len(by_hour) == 24 and by_hour[2] > by_hour[14]  # same incidents at 2 am and 2 pm, far fewer people at 2 am
    assert out[a]["intensity_by_hour"][2] == pytest.approx(out[a]["intensity_by_hour"][14], rel=0.01)
