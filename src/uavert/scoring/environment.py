"""Environment score from the Air Quality Health Index (AQHI)."""

from datetime import datetime, timedelta

from uavert.scoring.combine import Reason

# AQHI -> score, linear between points. Health Canada's bands (AQHI rounded: 1-3 low, 4-6 moderate,
# 7-10 high, 11+ very high) land in our lower / moderate / elevated / high bands.
BREAKPOINTS = ((1.0, 0.0), (3.5, 25.0), (6.5, 50.0), (10.5, 75.0), (15.0, 100.0))
STALE_AFTER = timedelta(hours=3)


def aqhi_score(aqhi: float) -> int:
    if aqhi <= BREAKPOINTS[0][0]:
        return 0
    for (x0, y0), (x1, y1) in zip(BREAKPOINTS, BREAKPOINTS[1:]):
        if aqhi <= x1:
            return round(y0 + (aqhi - x0) / (x1 - x0) * (y1 - y0))
    return 100


def health_canada_risk(aqhi: float) -> str:
    r = round(aqhi)
    return "low" if r <= 3 else "moderate" if r <= 6 else "high" if r <= 10 else "very high"


def environment(station_name: str | None, aqhi: float | None, observed_at: datetime | None,
                collected_at: str | None, now: datetime) -> tuple[int, list[Reason]]:
    if aqhi is None:
        return 0, [Reason("environment", "No current air quality reading", "eccc_aqhi")]
    stale = now - observed_at > STALE_AFTER
    text = f"Air Quality Health Index {aqhi:.0f} ({health_canada_risk(aqhi)} risk) at {station_name}"
    if stale:
        text += f" - not current, last reading {int((now - observed_at).total_seconds() // 3600)} h ago"
    return aqhi_score(aqhi), [Reason("environment", text, "eccc_aqhi", value=round(aqhi, 1),
                                     as_of=observed_at.isoformat(), collected_at=collected_at)]
