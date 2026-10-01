import pytest

from uavert.scoring import bands, crime
from uavert.scoring.combine import Reason, combine

W = {"murder": 7042, "robbery": 583, "assault_1": 23}


# Criterion 5: neighbourhood crime score = percentile rank of the CSI-weighted rate.
def test_weighted_rate_uses_csi_weights():
    # (2 x 583 + 10 x 23) / 20,000 x 100,000 = (1166 + 230) x 5 = 6,980
    assert crime.weighted_rate({"robbery": 2, "assault_1": 10}, W, 20_000) == pytest.approx(6980)


def test_percentile_rank_hand_worked():
    rates = {"A": 100.0, "B": 400.0, "C": 250.0, "D": 900.0}
    # ranks 0,2,1,3 of 3 -> 0, 67, 33, 100
    assert crime.percentile_scores(rates) == {"A": 0, "B": 67, "C": 33, "D": 100}


def test_percentile_ties_share_rank():
    assert crime.percentile_scores({"A": 1.0, "B": 1.0, "C": 5.0}) == {"A": 25, "B": 25, "C": 100}


def test_one_homicide_outweighs_many_minor_assaults():
    one_homicide = crime.weighted_rate({"murder": 1}, W, 10_000)
    many_assaults = crime.weighted_rate({"assault_1": 300}, W, 10_000)
    assert one_homicide > many_assaults


# Criterion 6: street cells — premises filter, recency, leaning toward the neighbourhood.
@pytest.mark.parametrize("premises,counts", [
    ("Outside", True), ("Transit", True), ("Commercial", True), (None, True),
    ("House", False), ("Apartment", False), ("Educational", False), ("Other", False),
])
def test_only_street_premises_count(premises, counts):
    assert crime.counts_on_street(premises) is counts


def test_recent_incidents_weigh_more():
    assert crime.recency_weight(0) == 1
    assert crime.recency_weight(180) == pytest.approx(0.5)
    assert crime.recency_weight(360) == pytest.approx(0.25)
    assert crime.recency_weight(-3) == 1  # dates after the newest incident don't count extra


def test_sparse_cell_leans_toward_neighbourhood():
    assert crime.lean_toward_neighbourhood(local=1000, incidents=0, neighbourhood_average=200) == 200
    assert crime.lean_toward_neighbourhood(local=1000, incidents=2, neighbourhood_average=200) == pytest.approx(520)
    assert crime.lean_toward_neighbourhood(local=1000, incidents=5, neighbourhood_average=200) == 1000


def test_local_value_adds_half_the_neighbour_average():
    own = {"a": 10.0, "b": 4.0, "c": 0.0}
    ring = {"a": ["b", "c", "outside-grid"], "b": ["a"], "c": ["a"]}
    local = crime.local_values(own, lambda c: ring[c])
    assert local == {"a": 10 + 0.5 * 2, "b": 4 + 0.5 * 10, "c": 0 + 0.5 * 10}


# Criterion 7: combined score is the highest category, never an average.
def test_combined_is_highest_not_average():
    s = combine({"crime": 10, "environment": 59}, [
        Reason("crime", "few incidents", "tps_mci"),
        Reason("environment", "AQHI 8 (high risk)", "eccc_aqhi"),
    ])
    assert s.score == 59 and s.band == "elevated"
    assert s.reasons[0].category == "environment"


def test_reasons_capped_at_three_and_two_per_category():
    reasons = [Reason("crime", f"c{i}", "tps_mci") for i in range(4)] + [Reason("environment", "e", "eccc_aqhi")]
    s = combine({"crime": 80, "environment": 30}, reasons)
    assert [r.text for r in s.reasons] == ["c0", "c1", "e"]


# Criterion 9: bands never say "safe".
def test_bands():
    assert [bands.band_for(x) for x in (0, 24, 25, 49, 50, 74, 75, 100)] == [
        "lower", "lower", "moderate", "moderate", "elevated", "elevated", "high", "high"]
    words = " ".join(list(bands.BAND_LABELS) + list(bands.BAND_LABELS.values())).lower()
    assert "safe" not in words
