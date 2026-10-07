"""Odds alongside the score (01-03-odds.md): one reported incident a year for every N residents, by severity."""

from collections.abc import Mapping

LEVELS = ("high", "medium", "low", "any")


def one_in(population: int | None, incidents: float) -> int | None:
    """Residents per reported incident: whole numbers below 100, two significant figures from 100 up.
    None when there were no incidents or no residents."""
    if not population or incidents <= 0:
        return None
    n = population / incidents
    if n < 100:
        return max(1, round(n))
    return int(round(n, 2 - len(str(int(n)))))


def by_level(counts: Mapping[str, float], severities: Mapping[str, str]) -> dict[str, float]:
    """Incidents per severity level, plus "any". `counts` is keyed by CSI offence."""
    out = dict.fromkeys(LEVELS, 0.0)
    for key, c in counts.items():
        out[severities[key]] += c
        out["any"] += c
    return out


def odds(counts: Mapping[str, float], population: int | None, toronto: Mapping[str, float],
         toronto_population: int, year: int) -> dict:
    """The neighbourhood's and Toronto's "1 in N" for each level. `counts` and `toronto` come from by_level."""
    return {"year": year, "population": population, "toronto_population": toronto_population,
            "levels": {level: {"incidents": round(counts[level], 1), "one_in": one_in(population, counts[level]),
                               "toronto_incidents": round(toronto[level], 1),
                               "toronto_one_in": one_in(toronto_population, toronto[level])}
                       for level in LEVELS}}
