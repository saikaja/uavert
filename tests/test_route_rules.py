import h3
import pytest

from uavert.scoring import route


def test_densify_leaves_no_gap_over_25m():
    pts = route.densify([(-79.390, 43.655), (-79.380, 43.655)])  # about 800 m east-west
    gaps = [route.distance_m(a, b) for a, b in zip(pts, pts[1:])]
    assert max(gaps) <= 25.01 and pts[0] == (-79.390, 43.655) and pts[-1] == (-79.380, 43.655)


def test_stretches_split_by_band_and_rank_riskiest():
    pts = route.densify([(-79.395, 43.655), (-79.365, 43.655)])
    cells = [route.cell_of(p) for p in pts]
    unique = list(dict.fromkeys(cells))
    # first third lower, middle third high, last third moderate
    k = len(unique) // 3
    scores = {c: 10 for c in unique[:k]} | {c: 90 for c in unique[k:2 * k]} | {c: 30 for c in unique[2 * k:]}
    runs = route.stretches(pts, scores)
    assert [r.band for r in runs] == ["lower", "high", "moderate"]
    top = route.riskiest(runs)
    assert [r.score for r in top] == [90, 30, 10]
    assert top[0].length_m > 100
    # stretches join end to end
    assert runs[0].points[-1] == runs[1].points[0]


def test_points_outside_grid_join_current_stretch():
    pts = route.densify([(-79.395, 43.655), (-79.385, 43.655)])
    first = route.cell_of(pts[0])
    runs = route.stretches(pts, {first: 40})
    assert len(runs) == 1 and runs[0].score == 40 and len(runs[0].points) == len(pts)
