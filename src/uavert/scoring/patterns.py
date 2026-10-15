"""Patterns in police reports (01-03-news.md): neighbourhoods where an offence ran well above its own usual level in
the latest 30 days of police data. Information only; nothing here changes a score."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from math import exp

OFFENCES = {"break_and_enter": "break-ins", "motor_vehicle_theft": "auto thefts"}
RECENT_DAYS = 30
USUAL_DAYS = 365  # the year before the recent 30 days
MIN_RECENT = 5
MIN_TIMES_USUAL = 2.0
MAX_CHANCE = 0.01  # less than a 1% chance of at least this many at the usual level
USUAL_FLOOR = 0.5  # per 30 days, so a quiet area can't divide by almost nothing


@dataclass(frozen=True)
class Pattern:
    area: str
    offence: str
    recent: int
    usual_per_30_days: float
    chance: float
    first_date: date
    last_date: date

    @property
    def times_usual(self) -> float:
        return self.recent / max(self.usual_per_30_days, USUAL_FLOOR)


def chance_of_at_least(k: int, mean: float) -> float:
    """Poisson: the chance of k or more events when mean are expected."""
    term, below = exp(-mean), 0.0
    for i in range(k):
        below += term
        term *= mean / (i + 1)
    return max(0.0, 1.0 - below)


def find(incidents: list[tuple[str, str, date]], newest: date) -> list[Pattern]:
    """`incidents`: (area, offence, Toronto date) for the offences in OFFENCES. `newest`: the police data's last day."""
    first = newest - timedelta(days=RECENT_DAYS - 1)
    usual_from = first - timedelta(days=USUAL_DAYS)
    recent, before = Counter(), Counter()
    for area, offence, day in incidents:
        if offence not in OFFENCES:
            continue
        if first <= day <= newest:
            recent[(area, offence)] += 1
        elif usual_from <= day < first:
            before[(area, offence)] += 1
    out = []
    for key, n in recent.items():
        usual = before[key] * RECENT_DAYS / USUAL_DAYS
        p = chance_of_at_least(n, max(usual, USUAL_FLOOR))
        if n >= MIN_RECENT and n >= MIN_TIMES_USUAL * usual and p < MAX_CHANCE:
            out.append(Pattern(key[0], key[1], n, usual, p, first, newest))
    return sorted(out, key=lambda x: x.chance)
