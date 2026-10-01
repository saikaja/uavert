"""Crime scoring rules: CSI weighting, percentile rank, recency and street-level smoothing."""

from bisect import bisect_left, bisect_right
from collections.abc import Callable, Hashable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import TypeVar

K = TypeVar("K", bound=Hashable)

HALF_LIFE_DAYS = 180  # an incident six months old counts half
RING_WEIGHT = 0.5  # weight of the 6 neighbouring cells (about 250 m) relative to the cell itself
MIN_INCIDENTS = 5  # below this, a cell's score leans toward its neighbourhood's
STREET_PREMISES = frozenset({"Outside", "Transit", "Commercial"})
HOMICIDE_YEARS = 3  # homicides are averaged over 3 years so one event doesn't swing a small area


def percentile_scores(values: Mapping[K, float]) -> dict[K, int]:
    """Rank each value against the others, 0 (lowest) to 100 (highest). Ties share the average rank."""
    n = len(values)
    if n < 2:
        return {k: 0 for k in values}
    ordered = sorted(values.values())
    out = {}
    for k, v in values.items():
        less = bisect_left(ordered, v)
        equal = bisect_right(ordered, v) - less
        rank = less + (equal - 1) / 2
        out[k] = round(100 * rank / (n - 1))
    return out


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


# ---- Foot traffic (design revision 3) and "compared with surroundings" (revision 2) ----

FOOT_TRAFFIC_FLOOR = 100.0  # pedestrians/hour; below this, counts can't show how many people are around
FOOT_TRAFFIC_SINCE = date(2015, 1, 1)
FOOT_TRAFFIC_MAX_RINGS = 3  # look up to about 600 m for counts
SURROUNDINGS_RINGS = 6  # about 1 km
BUSY_AREA_QUANTILE = 0.9
STANDOUT_MIN_RATIO = 1.5


@dataclass(frozen=True)
class FootTraffic:
    per_hour: float
    counts_used: int
    first_date: date | None
    last_date: date | None

    @property
    def estimated(self) -> bool:
        return self.counts_used == 0


def foot_traffic_estimate(cell: K, counts: Mapping[K, list[tuple[float, date]]], city_median: float,
                          disk: Callable[[K, int], Iterable[K]]) -> FootTraffic:
    """Median pedestrians/hour of counts within 1 ring of the cell, else 2, else 3, else the city median.
    `counts` maps a cell to its (pedestrians per hour, count date) pairs."""
    for k in range(1, FOOT_TRAFFIC_MAX_RINGS + 1):
        found = [c for n in disk(cell, k) for c in counts.get(n, [])]
        if found:
            dates = [d for _, d in found]
            return FootTraffic(median(v for v, _ in found), len(found), min(dates), max(dates))
    return FootTraffic(city_median, 0, None, None)


def per_person(value: float, pedestrians_per_hour: float) -> float:
    return value / max(pedestrians_per_hour, FOOT_TRAFFIC_FLOOR)


def surroundings_ratio(cell: K, values: Mapping[K, float], disk: Callable[[K, int], Iterable[K]]) -> float | None:
    """The cell's value divided by the median of the other cells within about 1 km. None when that median is 0."""
    around = [values[n] for n in disk(cell, SURROUNDINGS_RINGS) if n != cell and n in values]
    if not around:
        return None
    m = median(around)
    return values[cell] / m if m > 0 else None


def busy_area_threshold(location_rates: Iterable[float]) -> float:
    """Pedestrians/hour at the city's 90th percentile of counted locations."""
    ordered = sorted(location_rates)
    return ordered[min(len(ordered) - 1, int(BUSY_AREA_QUANTILE * len(ordered)))] if ordered else float("inf")


# ---- Time of day (01-03-time-of-day.md) ----

TIME_WINDOW = 3  # hours: the chosen hour and one either side
TIME_PRIOR_WEIGHT = 10  # incidents; a block with few nearby incidents follows Toronto's hourly pattern


def time_window(hour: int) -> tuple[int, int, int]:
    return ((hour - 1) % 24, hour, (hour + 1) % 24)


def window_shares(hours: Iterable[int | None], weights: Iterable[float]) -> list[float]:
    """For each hour, the weighted share of incidents in its 3-hour window. Incidents with no
    recorded time (None) count evenly across the day."""
    by_hour = [0.0] * 24
    untimed = 0.0
    for h, w in zip(hours, weights):
        if h is None:
            untimed += w
        else:
            by_hour[h] += w
    total = sum(by_hour) + untimed
    if total == 0:
        return [TIME_WINDOW / 24] * 24
    return [(sum(by_hour[w] for w in time_window(h)) + untimed * TIME_WINDOW / 24) / total for h in range(24)]


def lean_toward_city(cell_share: float, incidents: int, city_share: float) -> float:
    return (incidents * cell_share + TIME_PRIOR_WEIGHT * city_share) / (incidents + TIME_PRIOR_WEIGHT)


def intensity(share: float) -> float:
    """Incidents in a 3-hour window relative to an average 3 hours for the same block (1.0 = average)."""
    return share / (TIME_WINDOW / 24)


def per_person_at_hour(value: float, hour_intensity: float, pedestrians_per_hour: float, activity: float) -> float:
    return per_person(value * hour_intensity, pedestrians_per_hour * activity)
