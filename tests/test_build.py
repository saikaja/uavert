from datetime import UTC, datetime, timedelta

import h3
import pytest

from uavert.scoring.build import Event, cell_scores, counted, neighbourhood_scores

W = {"murder": 7042, "robbery": 583, "assault_1": 23, "theft_under_5000": 37}
T = datetime(2025, 6, 1, 16, tzinfo=UTC)


def ev(i, key, group, hood="1", cell=None, premises="Outside", when=T, weight=None):
    return Event(f"E{i}", "tps_mci", key, weight or W[key], group, premises, when, hood, cell)


def test_neighbourhood_scores_rank_csi_weighted_rates_and_explain_them():
    hoods = [
        {"id": 1, "external_id": "1", "population": 10_000, "counts": {"THEFTFROMMV": 10}},
        {"id": 2, "external_id": "2", "population": 10_000, "counts": {"THEFTFROMMV": 0}},
    ]
    events = [ev(1, "robbery", "robberies", "1"), ev(2, "assault_1", "assaults", "2"),
              ev(3, "robbery", "robberies", "2", when=datetime(2026, 2, 1, tzinfo=UTC))]  # 2026: not counted
    out = neighbourhood_scores(events, hoods, W, {"THEFTFROMMV": ("theft_under_5000", "thefts from vehicles")}, {})
    # hood 1: (583 + 10 x 37) / 10,000 x 100,000 = 9,530; hood 2: 23 x 10 = 230
    assert round(out[1]["weighted_rate"]) == 9530 and round(out[2]["weighted_rate"]) == 230
    # typical = median(9,530, 230) = 4,880 -> hood 1 is 1.95x typical: 25 + 20 x log2(1.95) = 44; hood 2 is 0.05x -> 0
    assert (out[1]["crime_score"], out[2]["crime_score"]) == (44, 0)
    texts = [r["text"] for r in out[1]["reasons"]]
    assert texts[0].startswith("About 2.0× the reported crime per resident of a typical Toronto neighbourhood")
    assert texts[1].startswith("1 robbery reported in 2025") and "Toronto median" in texts[1]
    assert all(r["as_of"] == "2025" for r in out[1]["reasons"])


def test_cell_scores_count_street_incidents_nearby_and_lean_when_sparse():
    centre = h3.latlng_to_cell(43.6536, -79.3840, 9)
    ring = list(h3.grid_ring(centre, 1))
    far = h3.latlng_to_cell(43.75, -79.30, 9)
    cells = {centre: 1, **{c: 1 for c in ring}, far: 1}
    newest = datetime(2026, 6, 30, tzinfo=UTC)
    events = (
        [ev(i, "robbery", "robberies", cell=centre, when=newest) for i in range(6)]
        + [ev(10, "robbery", "robberies", cell=centre, premises="House", when=newest)]  # inside a home: ignored
        + [ev(11, "robbery", "robberies", cell=centre, when=newest - timedelta(days=400))]  # older than 12 months
    )
    out = cell_scores(events, cells, {1: "Downtown"}, {})
    assert out[centre]["incident_count"] == 6
    assert out[centre]["own_value"] == 6 * 583
    assert out[centre]["crime_score"] >= 75  # far above the typical block
    assert out[centre]["reasons"][0]["text"].startswith("6 robberies within about 250 m")
    # far cell: no incidents nearby, so it takes the neighbourhood average and says so
    assert out[far]["incident_count"] == 0
    assert "leans on the Downtown average" in out[far]["reasons"][-1]["text"]
    assert out[far]["smoothed_value"] > 0


def test_cell_scores_allow_for_foot_traffic():
    a = h3.latlng_to_cell(43.6536, -79.3840, 9)
    b = h3.latlng_to_cell(43.70, -79.40, 9)  # far away, same raw incidents
    cells = {a: 1, b: 1}
    newest = datetime(2026, 6, 30, tzinfo=UTC)
    events = [ev(i, "robbery", "robberies", cell=a, when=newest) for i in range(6)] +              [ev(10 + i, "robbery", "robberies", cell=b, when=newest) for i in range(6)]
    traffic = [(a, 2000.0, datetime(2025, 5, 1).date()), (b, 50.0, datetime(2024, 5, 1).date())]
    out = cell_scores(events, cells, {1: "Test"}, {}, traffic)
    # same incidents, but 2,000 people an hour at a vs 50 (treated as the floor of 100) at b
    assert out[a]["per_person_value"] < out[b]["per_person_value"]
    assert out[a]["crime_score"] < out[b]["crime_score"]
    assert out[a]["foot_traffic"].per_hour == 2000 and out[a]["busy_area"]
    reason = out[a]["reasons"][1]
    assert reason["text"].startswith("About ") and "the reported street crime per person of a typical Toronto block" in reason["text"]
    assert "busy area with about 2,000 people an hour on foot (1 City of Toronto count, 2025)" in reason["text"]
    assert reason["source_key"] == "tps_mci"


def test_counted_uses_singular_for_one():
    assert counted(1, "robberies") == "1 robbery" and counted(2, "robberies") == "2 robberies"


def hom(i, when, hood="1", cell=None):
    return Event(f"H{i}", "tps_homicides", "murder", 7042, "homicides", None, when, hood, cell)


def test_neighbourhood_homicides_use_a_three_year_average():
    # Criterion 36: one homicide in 2025 now counts a third of what it did.
    hoods = [{"id": 1, "external_id": "1", "population": 10_000, "counts": {}},
             {"id": 2, "external_id": "2", "population": 10_000, "counts": {}}]
    one_2025 = neighbourhood_scores([hom(1, T)], hoods, {"murder": 7042}, {}, {})
    assert one_2025[1]["weighted_rate"] == pytest.approx(7042 / 3 / 10_000 * 100_000)
    text = one_2025[1]["reasons"][1]["text"]
    assert text.startswith("1 homicide in 2023-2025 (3-year average;") and one_2025[1]["reasons"][1]["as_of"] == "2023-2025"
    # homicides in 2023 and 2024 count too; 2022 doesn't
    spread = neighbourhood_scores([hom(1, datetime(2023, 3, 1, tzinfo=UTC)), hom(2, datetime(2024, 3, 1, tzinfo=UTC)),
                                   hom(3, datetime(2022, 3, 1, tzinfo=UTC))], hoods, {"murder": 7042}, {}, {})
    assert spread[1]["weighted_rate"] == pytest.approx(2 * 7042 / 3 / 10_000 * 100_000)


def test_street_homicides_count_a_third_for_three_years():
    # Criterion 37
    a = h3.latlng_to_cell(43.6536, -79.3840, 9)
    newest = datetime(2026, 6, 30, tzinfo=UTC)
    base = [ev(1, "robbery", "robberies", cell=a, when=newest)]
    two_years_ago = cell_scores(base + [hom(2, newest - timedelta(days=730), cell=a)], {a: 1}, {1: "Test"}, {})
    four_years_ago = cell_scores(base + [hom(3, newest - timedelta(days=1460), cell=a)], {a: 1}, {1: "Test"}, {})
    assert two_years_ago[a]["own_value"] == pytest.approx(583 + 7042 / 3)
    assert four_years_ago[a]["own_value"] == pytest.approx(583)
    assert any("1 homicide within about 250 m in the last 3 years" in r["text"] for r in two_years_ago[a]["reasons"])


def test_first_street_reason_is_the_most_frequent_offence():
    # Criterion 45: lead with what happens most, not the rarest serious event; the serious one still shows.
    a = h3.latlng_to_cell(43.6536, -79.3840, 9)
    newest = datetime(2026, 6, 30, tzinfo=UTC)
    events = [ev(i, "assault_1", "assaults", cell=a, when=newest) for i in range(5)] + [hom(9, newest - timedelta(days=30), cell=a)]
    reasons = [r["text"] for r in cell_scores(events, {a: 1}, {1: "Test"}, {})[a]["reasons"]]
    assert reasons[0].startswith("5 assaults within about 250 m")
    assert reasons[1].startswith("About ")  # how the block compares with a typical one
    assert any(t.startswith("1 homicide within about 250 m") for t in reasons)


def test_trends_are_attached_to_each_neighbourhood_with_toronto_and_source():
    import json
    from pathlib import Path

    from uavert.scoring.build import add_trends
    from uavert.sources import tps

    attrs = json.loads((Path(__file__).parent / "fixtures" / "tps" / "ncr_years_one.json").read_text())["attributes"]
    rows = [tps.CrimeYear("7", r.year, r.offence, r.count, r.rate_per_100k) for r in tps.parse_crime_years(attrs, 2014, 2025)]
    hood_rows = {7: {"details": {}}, 8: {"details": {}}}
    add_trends(hood_rows, rows, {"tps_ncr": {"collected_at": "2026-10-08T15:32:17+00:00"}})
    t = hood_rows[7]["details"]["trend"]
    assert t["windows"]["10"]["groups"]["violent"]["direction"] == "falling"
    assert t["toronto"]["series"]["all"][-1]["year"] == 2025
    assert (t["source_key"], t["collected_at"]) == ("tps_ncr", "2026-10-08T15:32:17+00:00")
    assert "trend" not in hood_rows[8]["details"]  # no yearly figures for it


def test_no_yearly_figures_adds_no_trend():
    from uavert.scoring.build import add_trends

    hood_rows = {7: {"details": {}}}
    add_trends(hood_rows, [], {})
    assert hood_rows[7]["details"] == {}


def test_trends_wait_for_the_scoring_year_to_be_published(capsys):
    # review finding: when the scoring year moves on before Toronto Police publishes it, scores still build
    import json
    from pathlib import Path

    from uavert.scoring import build
    from uavert.sources import tps

    attrs = json.loads((Path(__file__).parent / "fixtures" / "tps" / "ncr_years_one.json").read_text())["attributes"]
    rows = [tps.CrimeYear("7", r.year, r.offence, r.count, r.rate_per_100k)
            for r in tps.parse_crime_years(attrs, 2014, 2025) if r.year < 2025]
    hood_rows = {7: {"details": {}}}
    build.add_trends(hood_rows, rows, {})
    assert hood_rows[7]["details"] == {}
    assert "no trends" in capsys.readouterr().out
