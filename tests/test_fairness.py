import pytest

from uavert.ingest.reference import DATA_DIR, read_csv
from uavert.scoring import fairness


def test_spearman_known_values():
    assert fairness.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert fairness.spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    # hand-worked: ranks x 1..5, y ranks 2,1,4,3,5 -> d^2 sum 4 -> 1 - 6*4/(5*24) = 0.8
    assert fairness.spearman([1, 2, 3, 4, 5], [20, 10, 40, 30, 50]) == pytest.approx(0.8)


def test_ties_share_rank_and_degenerate_cases():
    assert fairness.ranks([5, 1, 5, 3]) == [3.5, 1.0, 3.5, 2.0]
    assert fairness.spearman([1, 1, 1], [1, 2, 3]) is None  # no spread
    assert fairness.spearman([1, 2], [1, 2]) is None  # too few


def test_label_uses_the_build_plan_threshold():
    # Criterion 35
    assert fairness.label(-0.28, 0.24) == fairness.OK_LABEL
    assert fairness.label(-0.62, 0.1) == fairness.REVIEW_LABEL
    assert fairness.label(0.1, 0.5) == fairness.REVIEW_LABEL
    assert fairness.label(None, None) == fairness.OK_LABEL


def test_income_file_has_every_neighbourhood_with_source_and_date():
    rows = read_csv(DATA_DIR / "neighbourhood_income_2021.csv")
    assert len(rows) == 158 and all(float(r["median_household_income"]) > 0 for r in rows)
    head = (DATA_DIR / "neighbourhood_income_2021.csv").read_text(encoding="utf-8")
    assert "neighbourhood-profiles" in head and "Retrieved: 2026-10-01" in head
