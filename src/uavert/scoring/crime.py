"""Crime scoring rules: CSI weighting, percentile rank, recency and street-level smoothing."""

from bisect import bisect_left, bisect_right
from collections.abc import Callable, Hashable, Iterable, Mapping
from typing import TypeVar

K = TypeVar("K", bound=Hashable)

HALF_LIFE_DAYS = 180  # an incident six months old counts half
RING_WEIGHT = 0.5  # weight of the 6 neighbouring cells (about 250 m) relative to the cell itself
MIN_INCIDENTS = 5  # below this, a cell's score leans toward its neighbourhood's
STREET_PREMISES = frozenset({"Outside", "Transit", "Commercial"})


def percentile_scores(values: Mapping[K, float]) -> dict[K, int]:
    """Rank each value against the others, 0 (lowest) to 100 (highest). Ties share the average rank."""
    n = len(values)
    if n < 2:
        return {k: 0 for k in values}
    ordered = sorted(values.values())
    out = {}
    for k, v in values.items():
        less = _count_less(ordered, v)
        equal = _count_less(ordered, v, inclusive=True) - less
        rank = less + (equal - 1) / 2
        out[k] = round(100 * rank / (n - 1))
    return out


def _count_less(ordered: list[float], v: float, inclusive: bool = False) -> int:
    return (bisect_right if inclusive else bisect_left)(ordered, v)


def weighted_rate(counts: Mapping[str, float], weights: Mapping[str, float], population: int) -> float:
    """CSI-weighted crimes per 100,000 residents. `counts` is keyed by CSI offence."""
    if not population:
        return 0.0
    return sum(c * weights[k] for k, c in counts.items()) / population * 100_000


def counts_on_street(premises_type: str | None) -> bool:
    """Street scores count incidents outside, on transit or in commercial places. Shootings and
    homicides have no premises type and always count; incidents inside homes never do."""
    return premises_type is None or premises_type in STREET_PREMISES


def recency_weight(age_days: float, half_life_days: float = HALF_LIFE_DAYS) -> float:
    return 0.5 ** (max(age_days, 0.0) / half_life_days)


def local_values(own: Mapping[K, float], neighbours: Callable[[K], Iterable[K]]) -> dict[K, float]:
    """A cell's value plus RING_WEIGHT times the average of its neighbours inside the grid."""
    out = {}
    for cell, value in own.items():
        ring = [own[n] for n in neighbours(cell) if n in own]
        out[cell] = value + RING_WEIGHT * (sum(ring) / len(ring) if ring else 0.0)
    return out


def lean_toward_neighbourhood(local: float, incidents: int, neighbourhood_average: float) -> float:
    """With MIN_INCIDENTS or more nearby incidents a cell stands on its own; with fewer it blends
    toward its neighbourhood's average, reaching the average itself at 0 incidents."""
    if incidents >= MIN_INCIDENTS:
        return local
    share = incidents / MIN_INCIDENTS
    return share * local + (1 - share) * neighbourhood_average
