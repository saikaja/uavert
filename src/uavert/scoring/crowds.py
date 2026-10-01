"""Big crowds: large City events on their dates (a moderate score nearby) and major venues (context only)."""

from dataclasses import dataclass
from datetime import date

from uavert.scoring.combine import Reason
from uavert.scoring.route import distance_m

EVENT_SCORE = 35  # moderate: crowds and road closures, not danger in themselves
EVENT_RADIUS_M = 1000
VENUE_RADIUS_M = 500


@dataclass(frozen=True)
class CrowdEvent:
    name: str
    event_date: date
    lon: float
    lat: float
    collected_at: str | None = None


@dataclass(frozen=True)
class Venue:
    name: str
    capacity: int
    lon: float
    lat: float


def crowds_score(lon: float, lat: float, on: date, events: list[CrowdEvent], venues: list[Venue],
                 today: date) -> tuple[int, list[Reason]]:
    reasons = []
    near_events = sorted((distance_m((lon, lat), (e.lon, e.lat)), e) for e in events
                         if e.event_date == on and distance_m((lon, lat), (e.lon, e.lat)) <= EVENT_RADIUS_M)
    for d, e in near_events[:1]:
        when = "today" if on == today else f"on {on:%a %b} {on.day}"
        reasons.append(Reason("crowds", f"{e.name} {when}, about {d:,.0f} m away: large crowds and road closures expected",
                              "toronto_events", value=e.name, as_of=on.isoformat(), collected_at=e.collected_at))
    for d, v in sorted((distance_m((lon, lat), (v.lon, v.lat)), v) for v in venues
                       if distance_m((lon, lat), (v.lon, v.lat)) <= VENUE_RADIUS_M)[:1]:
        reasons.append(Reason("crowds", f"Near {v.name}: can draw about {v.capacity:,} people on event days",
                              "major_venues", value=v.capacity))
    return (EVENT_SCORE if near_events else 0), reasons
