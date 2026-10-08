import json
from pathlib import Path

import pytest

from uavert.scoring import trends
from uavert.sources import tps

FIX = Path(__file__).parent / "fixtures" / "tps"


def yonge_bay() -> list[tps.CrimeYear]:
    attrs = json.loads((FIX / "ncr_years_one.json").read_text())["attributes"]
    return tps.parse_crime_years(attrs, 2014, 2025)


def test_flat_series_has_no_change():
    assert trends.fitted_change([5.0] * 10) == 0


def test_straight_line_change_is_exact():
    # 10 -> 15 in a straight line: +50%; 20 -> 10: -50%
    assert trends.fitted_change([10, 11, 12, 13, 14, 15]) == 50
    assert trends.fitted_change([20, 17.5, 15, 12.5, 10]) == -50


def test_one_odd_year_moves_the_line_less_than_end_to_end():
    # end to end this is +100%; the fitted line, less affected by the last point, says less
    assert 0 < trends.fitted_change([10, 10, 10, 10, 10, 20]) < 100


def test_no_fitted_change_from_zero():
    assert trends.fitted_change([0, 0, 0, 1, 2]) is None


@pytest.mark.parametrize(("change", "avg", "expected"), [
    (10, 50, "rising"), (9, 50, "flat"), (-9, 50, "flat"), (-10, 50, "falling"),
    (40, 9.9, "too_few"), (40, 10, "rising"), (None, 50, "too_few"),
])
def test_direction_thresholds(change, avg, expected):
    assert trends.direction(change, avg) == expected


def test_population_is_recovered_from_count_and_rate():
    pops = trends.populations(yonge_bay())
    assert round(pops[("170", 2025)]) == 16661  # published POPULATION_2025
    assert round(pops[("170", 2014)], -2) == 10300


def test_neighbourhood_group_rates_and_changes_match_the_published_figures():
    hood, toronto = trends.trends(yonge_bay(), last_year=2025)
    t = hood["170"]
    violent = {p["year"]: p for p in t["series"]["violent"]}
    assert sorted(violent) == list(range(2016, 2026))
    assert violent[2016]["rate_per_1000"] == 47.45  # 474.5 per 100,000, summed from the published rates
    assert violent[2025]["count"] == 614
    assert t["windows"]["10"]["groups"]["violent"]["change_pct"] == -38
    assert t["windows"]["10"]["groups"]["violent"]["direction"] == "falling"
    assert t["windows"]["5"]["groups"]["violent"]["change_pct"] == 31
    assert t["windows"]["5"]["groups"]["property"]["change_pct"] == -26
    assert (t["windows"]["5"]["first_year"], t["windows"]["5"]["last_year"]) == (2021, 2025)


def test_small_offences_are_too_few_to_call():
    hood, _ = trends.trends(yonge_bay(), last_year=2025)
    homicide = hood["170"]["windows"]["10"]["offences"]["HOMICIDE"]
    assert homicide["direction"] == "too_few" and homicide["count_last_year"] >= 0


def test_toronto_is_all_neighbourhoods_together():
    rows = yonge_bay()
    twin = [tps.CrimeYear("999", r.year, r.offence, r.count, r.rate_per_100k) for r in rows]
    hood, toronto = trends.trends(rows + twin, last_year=2025)
    # two identical neighbourhoods: Toronto's rate equals each one's, and its counts double
    assert toronto["series"]["violent"][-1]["rate_per_1000"] == pytest.approx(hood["170"]["series"]["violent"][-1]["rate_per_1000"], abs=0.1)
    assert toronto["series"]["violent"][-1]["count"] == 2 * 614
    assert toronto["windows"]["10"]["groups"]["violent"]["change_pct"] == -38
