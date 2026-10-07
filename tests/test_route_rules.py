from uavert.scoring import route


def test_densify_leaves_no_gap_over_25m():
    pts = route.densify([(-79.390, 43.655), (-79.380, 43.655)])  # about 800 m east-west
    gaps = [route.distance_m(a, b) for a, b in zip(pts, pts[1:])]
    assert max(gaps) <= 25.01 and pts[0] == (-79.390, 43.655) and pts[-1] == (-79.380, 43.655)


def walk():
    pts = route.densify([(-79.400, 43.655), (-79.370, 43.655)])  # about 2.4 km, 10+ cells
    return pts, [cell for cell, _ in route.cells_in_order(pts)]


def test_cells_in_order_joins_pieces_end_to_end():
    pts, cells = walk()
    groups = route.cells_in_order(pts)
    assert len(groups) == len(cells) and groups[0][1][-1] == groups[1][1][0]


def test_standout_stretches_ranked_thresholded_and_joined():
    pts, cells = walk()
    ratios = {c: 1.0 for c in cells}
    ratios[cells[1]], ratios[cells[2]] = 2.0, 3.0  # two neighbours: one stretch, worst 3.0
    ratios[cells[5]] = 1.4  # below 1.5: not a stretch
    ratios[cells[7]] = 1.6
    ratios[cells[-1]] = None  # quiet surroundings: never a stretch
    out = route.standout_stretches(pts, ratios)
    assert [s.ratio for s in out] == [3.0, 1.6]
    assert out[0].worst_cell == cells[2] and out[0].length_m > 100


def test_at_most_three_stretches():
    pts, cells = walk()
    ratios = {c: (2.0 + i if i % 2 == 0 else 1.0) for i, c in enumerate(cells)}  # every other cell stands out
    out = route.standout_stretches(pts, ratios)
    assert len(out) == 3 and out[0].ratio > out[1].ratio > out[2].ratio


def test_nothing_stands_out():
    pts, cells = walk()
    assert route.standout_stretches(pts, {c: 1.2 for c in cells}) == []


def test_typical_score_is_the_length_weighted_median():
    # Criterion 44: most of the walk is moderate, one short block is elevated.
    pts, cells = walk()
    scores = {c: 40 for c in cells}
    scores[cells[3]] = 70
    assert route.typical_score(pts, scores) == 40
    assert route.typical_score(pts, {}) is None
