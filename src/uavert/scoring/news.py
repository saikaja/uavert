"""News score: a located, unverified report raises nearby cells for 24 hours, never above "elevated"."""

from dataclasses import dataclass
from datetime import datetime

import h3

from uavert.scoring.combine import Reason

CAPS = {"violent_incident": 74, "protest": 60}  # 74 is the top of "elevated"; only official alerts reach "high"
WINDOW_HOURS = 24.0
RING = 2  # cells within 2 rings, about 500 m


@dataclass(frozen=True)
class NewsSignal:
    headline: str
    url: str
    publisher: str
    category: str
    published_at: datetime
    h3: str
    neighbourhood_id: int | None = None
    collected_at: str | None = None


def signal_strength(s: NewsSignal, now: datetime) -> float:
    hours = (now - s.published_at).total_seconds() / 3600
    if hours < 0:
        hours = 0.0
    if hours >= WINDOW_HOURS:
        return 0.0
    return CAPS[s.category] * (1 - hours / WINDOW_HOURS)


def _near(a: str, b: str) -> bool:
    try:
        return h3.grid_distance(a, b) <= RING
    except Exception:  # cells too far apart to measure
        return False


def news_score(signals: list[NewsSignal], now: datetime, cell: str | None = None,
               neighbourhood_id: int | None = None) -> tuple[int, list[Reason]]:
    """For a cell: reports within about 500 m. For a neighbourhood: reports inside it."""
    hits = []
    for s in signals:
        relevant = _near(cell, s.h3) if cell else (neighbourhood_id is not None and s.neighbourhood_id == neighbourhood_id)
        strength = signal_strength(s, now) if relevant else 0.0
        if strength > 0:
            hits.append((strength, s))
    hits.sort(key=lambda x: -x[0])
    reasons = [
        Reason("news", f"Unverified news report: {s.headline} ({s.publisher}, "
               f"{max(0, int((now - s.published_at).total_seconds() // 3600))} h ago)",
               "news_cbc" if s.publisher == "CBC News" else "news_gdelt", value=s.category,
               as_of=s.published_at.isoformat(), collected_at=s.collected_at, url=s.url)
        for _, s in hits
    ]
    return (round(hits[0][0]) if hits else 0), reasons
