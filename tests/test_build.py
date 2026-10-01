from datetime import UTC, datetime, timedelta

import h3

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
    assert (out[1]["crime_score"], out[2]["crime_score"]) == (100, 0)
    texts = [r["text"] for r in out[1]["reasons"]]
    assert texts[0].startswith("1 robbery reported in 2025") and "Toronto median" in texts[0]
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
    assert out[centre]["crime_score"] == 100
    assert out[centre]["reasons"][0]["text"].startswith("6 robberies within about 250 m")
    # far cell: no incidents nearby, so it takes the neighbourhood average and says so
    assert out[far]["incident_count"] == 0
    assert "leans on the Downtown average" in out[far]["reasons"][-1]["text"]
    assert out[far]["smoothed_value"] > 0


def test_counted_uses_singular_for_one():
    assert counted(1, "robberies") == "1 robbery" and counted(2, "robberies") == "2 robberies"
