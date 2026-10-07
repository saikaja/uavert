from datetime import UTC, datetime

import pytest

from uavert.scoring.build import Event, neighbourhood_scores
from uavert.scoring.odds import by_level, one_in

W = {"murder": 7042, "robbery": 583, "assault_1": 23, "theft_under_5000": 37}
SEVERITY = {"murder": "high", "robbery": "high", "assault_1": "medium", "theft_under_5000": "low"}
T = datetime(2025, 6, 1, 16, tzinfo=UTC)


def test_one_in_rounds_to_two_significant_figures_from_100():
    assert one_in(3_214_722, 47_201) == 68
    assert one_in(84, 1) == 84
    assert one_in(3_214_722, 7_211) == 450  # 445.8
    assert one_in(1_234, 1) == 1_200
    assert one_in(3_214_722, 1) == 3_200_000
    assert one_in(10, 30) == 1  # never "1 in 0"


def test_one_in_is_none_without_incidents_or_residents():
    assert one_in(10_000, 0) is None and one_in(0, 5) is None and one_in(None, 5) is None


def test_by_level_sums_offences_into_levels_and_any():
    counts = {"robbery": 2, "murder": 1 / 3, "assault_1": 5, "theft_under_5000": 10}
    assert by_level(counts, SEVERITY) == pytest.approx({"high": 2 + 1 / 3, "medium": 5, "low": 10, "any": 17 + 1 / 3})


def test_neighbourhood_odds_per_resident_with_toronto_alongside():
    hoods = [
        {"id": 1, "external_id": "1", "population": 10_000, "counts": {"THEFTFROMMV": 10}},
        {"id": 2, "external_id": "2", "population": 10_000, "counts": {"THEFTFROMMV": 0}},
    ]
    events = [Event("E1", "tps_mci", "robbery", 583, "robberies", "Outside", T, "1", None),
              Event("E2", "tps_mci", "assault_1", 23, "assaults", "Outside", T, "2", None),
              Event("H1", "tps_homicides", "murder", 7042, "homicides", None, T, "2", None)]
    out = neighbourhood_scores(events, hoods, W, {"THEFTFROMMV": ("theft_under_5000", "thefts from vehicles")}, {},
                               SEVERITY)
    odds = out[1]["details"]["odds"]
    assert (odds["year"], odds["population"], odds["toronto_population"]) == (2025, 10_000, 20_000)
    high, medium, low, any_ = (odds["levels"][k] for k in ("high", "medium", "low", "any"))
    # hood 1: 1 robbery, 10 thefts from vehicles; Toronto adds hood 2's assault and a third of a homicide
    assert (high["incidents"], high["one_in"], high["toronto_one_in"]) == (1, 10_000, 15_000)  # 20,000 / 1.33
    assert (medium["incidents"], medium["one_in"], medium["toronto_one_in"]) == (0, None, 20_000)
    assert (low["one_in"], low["toronto_one_in"]) == (1_000, 2_000)
    assert (any_["incidents"], any_["one_in"], any_["toronto_one_in"]) == (11, 910, 1_600)  # 909; 20,000 / 12.33
    assert out[2]["details"]["odds"]["levels"]["high"]["incidents"] == 0.3
