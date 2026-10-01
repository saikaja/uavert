"""Route scoring: sample the route every 25 m, map samples to H3 cells, find the stretches that
stand out from their surroundings (design revision 2)."""

import math
from dataclasses import dataclass, field

import h3

from uavert.scoring.crime import STANDOUT_MIN_RATIO

STEP_M = 25.0
MAX_STRETCHES = 3


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    (lon1, lat1), (lon2, lat2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 12_742_000 * math.asin(math.sqrt(h))


def densify(coords: list[tuple[float, float]], step_m: float = STEP_M) -> list[tuple[float, float]]:
    """The route's points plus extra points so no gap is longer than step_m."""
    if not coords:
        return []
    out = [coords[0]]
    for a, b in zip(coords, coords[1:]):
        n = max(1, math.ceil(distance_m(a, b) / step_m))
        out += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(1, n + 1)]
    return out


def cell_of(point: tuple[float, float]) -> str:
    return h3.latlng_to_cell(point[1], point[0], 9)


def cells_in_order(points: list[tuple[float, float]]) -> list[tuple[str, list[tuple[float, float]]]]:
    """Group consecutive route points by the cell they fall in."""
    groups: list[tuple[str, list[tuple[float, float]]]] = []
    for p in points:
        cell = cell_of(p)
        if groups and groups[-1][0] == cell:
            groups[-1][1].append(p)
        else:
            if groups:
                groups[-1][1].append(p)  # keep pieces joined end to end
            groups.append((cell, [p]))
    return groups


@dataclass
class Stretch:
    ratio: float
    worst_cell: str
    points: list[tuple[float, float]] = field(default_factory=list)

    @property
    def length_m(self) -> float:
        return sum(distance_m(a, b) for a, b in zip(self.points, self.points[1:]))


def standout_stretches(points: list[tuple[float, float]], ratios: dict[str, float | None]) -> list[Stretch]:
    """Runs of consecutive cells at least STANDOUT_MIN_RATIO times their surroundings, the ones that
    stand out most first, at most MAX_STRETCHES."""
    runs: list[Stretch] = []
    previous_qualified = False
    for cell, pts in cells_in_order(points):
        ratio = ratios.get(cell)
        if ratio is None or ratio < STANDOUT_MIN_RATIO:
            previous_qualified = False
            continue
        if previous_qualified:
            run = runs[-1]
            run.points += pts
            if ratio > run.ratio:
                run.ratio, run.worst_cell = ratio, cell
        else:
            runs.append(Stretch(ratio, cell, list(pts)))
        previous_qualified = True
    return sorted(runs, key=lambda s: -s.ratio)[:MAX_STRETCHES]
