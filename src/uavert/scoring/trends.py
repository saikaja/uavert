"""Crime trendlines (01-03-trends.md): reported crime per resident over the last 10 and 5 years, with a fitted line."""

from collections import defaultdict
from collections.abc import Iterable
from statistics import median

from uavert.sources.tps import CrimeYear

GROUPS = {
    "violent": ("ASSAULT", "ROBBERY", "HOMICIDE", "SHOOTING"),
    "property": ("BREAKENTER", "AUTOTHEFT", "THEFTOVER", "THEFTFROMMV", "BIKETHEFT"),
}
GROUPS["all"] = GROUPS["violent"] + GROUPS["property"]
WINDOWS = (10, 5)  # years; the chart shows the longer one
FLAT_WITHIN = 10  # percent either way counts as roughly flat
MIN_PER_YEAR = 10  # fewer incidents a year on average is too few to call a trend


def fitted_change(values: list[float]) -> int | None:
    """Percent change of the least-squares line from the first year to the last. None if the line starts at or below 0."""
    n = len(values)
    mx, my = (n - 1) / 2, sum(values) / n
    slope = sum((x - mx) * (v - my) for x, v in enumerate(values)) / sum((x - mx) ** 2 for x in range(n))
    start, end = my - slope * mx, my + slope * mx
    return round((end - start) / start * 100) if start > 0 else None


def direction(change: int | None, avg_per_year: float) -> str:
    if change is None or avg_per_year < MIN_PER_YEAR:
        return "too_few"
    return "rising" if change >= FLAT_WITHIN else "falling" if change <= -FLAT_WITHIN else "flat"


def populations(rows: Iterable[CrimeYear]) -> dict[tuple[str, int], float]:
    """Residents per (neighbourhood, year), recovered as count / rate x 100,000 (median over offences with incidents)."""
    found = defaultdict(list)
    for r in rows:
        if r.count and r.rate_per_100k:
            found[(r.hood_external_id, r.year)].append(r.count / r.rate_per_100k * 100_000)
    return {k: median(v) for k, v in found.items()}


def _summary(points: list[dict]) -> dict:
    """Change and direction for one window of {year, rate_per_1000, count} points."""
    change = fitted_change([p["rate_per_1000"] for p in points])
    avg = sum(p["count"] for p in points) / len(points)
    return {"change_pct": change, "direction": direction(change, avg), "avg_per_year": round(avg, 1)}


def _windows(series: dict[str, list[dict]], offences: dict[str, list[dict]] | None, last_year: int) -> dict:
    out = {}
    for w in WINDOWS:
        first = last_year - w + 1
        cut = lambda pts: [p for p in pts if p["year"] >= first]
        out[str(w)] = {"first_year": first, "last_year": last_year,
                       "groups": {g: _summary(cut(pts)) for g, pts in series.items()}}
        if offences is not None:
            out[str(w)]["offences"] = {k: _summary(cut(pts)) | {"count_last_year": pts[-1]["count"]}
                                       for k, pts in offences.items()}
    return out


def trends(rows: list[CrimeYear], last_year: int) -> tuple[dict[str, dict], dict]:
    """Per neighbourhood (keyed like the rows) and for Toronto: yearly series for each group and the fitted change
    over each window. Neighbourhood rates are the published per-100,000 rates summed, shown per 1,000 residents."""
    first_year = last_year - max(WINDOWS) + 1
    rows = [r for r in rows if first_year <= r.year <= last_year]
    figures = {(r.hood_external_id, r.year, r.offence): r for r in rows}
    pops = populations(rows)
    years = range(first_year, last_year + 1)
    # Only neighbourhoods with every figure; one with a gap gets no trend (and isn't counted in Toronto's).
    hood_ids = sorted(h for h in {r.hood_external_id for r in rows}
                      if all((h, y, k) in figures for y in years for k in GROUPS["all"]))

    def point(year, offences, hood):
        figs = [figures[(hood, year, k)] for k in offences]
        return {"year": year, "count": sum(f.count for f in figs),
                "rate_per_1000": round(sum(f.rate_per_100k for f in figs) / 100, 2)}

    per_hood = {}
    for h in hood_ids:
        series = {g: [point(y, ks, h) for y in years] for g, ks in GROUPS.items()}
        offences = {k: [point(y, (k,), h) for y in years] for k in GROUPS["all"]}
        per_hood[h] = {"series": series, "windows": _windows(series, offences, last_year)}

    toronto_series = {}
    for g, ks in GROUPS.items():
        pts = []
        for y in years:
            count = sum(figures[(h, y, k)].count for h in hood_ids for k in ks)
            pop = sum(pops.get((h, y), 0) for h in hood_ids)
            pts.append({"year": y, "count": count, "rate_per_1000": round(count / pop * 1000, 2) if pop else 0.0,
                        "population": round(pop)})
        toronto_series[g] = pts
    return per_hood, {"series": toronto_series, "windows": _windows(toronto_series, None, last_year)}
