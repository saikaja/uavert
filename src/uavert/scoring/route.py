"""Route scoring: sample the route every 25 m, map samples to H3 cells, find the riskiest stretches."""

import math
from dataclasses import dataclass, field

import h3

from uavert.scoring.bands import band_for

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


@dataclass
class Stretch:
    score: int
    band: str
    worst_cell: str
    points: list[tuple[float, float]] = field(default_factory=list)

    @property
    def length_m(self) -> float:
        return sum(distance_m(a, b) for a, b in zip(self.points, self.points[1:]))


def stretches(points: list[tuple[float, float]], scores: dict[str, int]) -> list[Stretch]:
    """Split the route into runs of consecutive points whose cells share a band. Points in cells
    without a score (outside the grid) join the run they're in without changing it."""
    runs: list[Stretch] = []
    for p in points:
        cell = cell_of(p)
        score = scores.get(cell)
        if runs and (score is None or band_for(score) == runs[-1].band):
            run = runs[-1]
            run.points.append(p)
            if score is not None and score > run.score:
                run.score, run.worst_cell = score, cell
        elif score is not None:
            if runs:
                runs[-1].points.append(p)  # keep stretches joined end to end
            runs.append(Stretch(score, band_for(score), cell, [p]))
    return runs


def riskiest(runs: list[Stretch], n: int = MAX_STRETCHES) -> list[Stretch]:
    return sorted(runs, key=lambda s: (-s.score, -s.length_m))[:n]
