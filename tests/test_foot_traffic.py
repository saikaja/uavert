from datetime import date
from pathlib import Path

import pytest

from uavert.scoring import crime
from uavert.sources.toronto_open_data import parse_tmc_csv

FIX = Path(__file__).parent / "fixtures" / "traffic" / "tmc_sample.csv"


def test_parse_real_sample_normalises_to_per_hour():
    counts = parse_tmc_csv(FIX.read_text(encoding="utf-8"))
    assert len(counts) == 17  # 17 real rows, all with coordinates, all distinct locations
    first = counts[0]
    assert first.location_name == "Worthington Cres / South Kingsway (South)"
    assert first.count_date == date(2026, 9, 23) and first.hours == 14.0 and first.pedestrians == 214
    assert first.pedestrians_per_hour == pytest.approx(214 / 14)
    assert {c.hours for c in counts} == {8.0, 14.0}  # '8R' and '8S' are 8-hour counts


def test_parse_skips_rows_without_coordinates_and_keeps_latest_per_location():
    header = FIX.read_text(encoding="utf-8").splitlines()[0]
    cols = header.split(",")

    def row(**v):
        base = dict.fromkeys(cols, "")
        base.update(centreline_type="2", centreline_id="1", location_name="A / B", latest_count_id="1",
                    count_duration="14", total_pedestrian="140", total_bike="0", total_vehicle="0",
                    latitude="43.65", longitude="-79.38")
        base.update(v)
        return ",".join(base[c] for c in cols)

    text = "\n".join([header, row(latest_count_date="2019-05-01"), row(latest_count_date="2024-05-01", total_pedestrian="280"),
                      row(centreline_id="2", latest_count_date="2024-05-01", latitude="", longitude="")])
    counts = parse_tmc_csv(text)
    assert len(counts) == 1 and counts[0].count_date == date(2024, 5, 1) and counts[0].pedestrians_per_hour == 20


GRID = {  # a toy grid: ring k of "x" is the cells listed at distance <= k
    ("x", 1): ["x", "a"], ("x", 2): ["x", "a", "b"], ("x", 3): ["x", "a", "b", "c"],
}


def disk(cell, k):
    return GRID.get((cell, k), [cell])


def test_foot_traffic_widens_search_then_falls_back_to_city_median():
    d = date(2024, 1, 1)
    assert crime.foot_traffic_estimate("x", {"a": [(300.0, d), (100.0, date(2020, 1, 1))]}, 40, disk) == \
        crime.FootTraffic(200.0, 2, date(2020, 1, 1), d)
    assert crime.foot_traffic_estimate("x", {"c": [(90.0, d)]}, 40, disk).per_hour == 90.0  # found at 3 rings
    est = crime.foot_traffic_estimate("x", {}, 40, disk)
    assert est.per_hour == 40 and est.estimated


def test_per_person_uses_floor_of_100():
    assert crime.per_person(1000, 1000) == 1.0
    assert crime.per_person(1000, 25) == 10.0  # 25 people/hour is treated as 100


def test_surroundings_ratio():
    values = {"x": 6.0, "a": 2.0, "b": 3.0, "c": 4.0}
    ring = {"x": ["x", "a", "b", "c"]}
    assert crime.surroundings_ratio("x", values, lambda c, k: ring[c]) == 2.0  # 6 / median(2, 3, 4)
    assert crime.surroundings_ratio("x", {"x": 5.0, "a": 0.0, "b": 0.0, "c": 1.0}, lambda c, k: ring[c]) is None


def test_busy_area_threshold_is_90th_percentile():
    assert crime.busy_area_threshold(range(1, 101)) == 91
    assert crime.busy_area_threshold([]) == float("inf")
