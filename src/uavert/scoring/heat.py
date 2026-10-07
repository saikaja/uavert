"""Extreme heat: during a heat alert, point people to the nearest cool space open at that time."""

from dataclasses import dataclass
from datetime import datetime

from uavert.scoring.combine import Reason
from uavert.scoring.route import distance_m

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
SEARCH_M = 3000


@dataclass(frozen=True)
class CoolSpace:
    name: str
    kind: str
    lon: float
    lat: float
    hours: dict  # {"mon": ["0900", "2030"] | "call" | None, ...}


def is_heat_alert(name: str) -> bool:
    return "heat" in name.lower()


def open_status(hours: dict, when: datetime) -> tuple[str, str | None]:
    """('open', closing time 'HH:MM') / ('call', None) / ('closed', None) at a local time."""
    day = hours.get(WEEKDAYS[when.weekday()])
    if day == "call":
        return "call", None
    if not day or len(day) != 2:
        return "closed", None
    opens, closes = day
    now = when.strftime("%H%M")
    if opens <= now < closes:
        return "open", f"{closes[:2]}:{closes[2:]}"
    return "closed", None


def nearest_open(spaces: list[CoolSpace], lon: float, lat: float, when: datetime) -> tuple[CoolSpace, float, str] | None:
    """The nearest space within SEARCH_M that is open (or asks you to call) at `when`, with its distance and status."""
    found = []
    for s in spaces:
        d = distance_m((lon, lat), (s.lon, s.lat))
        if d <= SEARCH_M:
            status, closes = open_status(s.hours, when)
            if status != "closed":
                found.append((d, s, status, closes))
    if not found:
        return None
    d, s, status, closes = min(found, key=lambda x: (x[2] != "open", x[0]))  # prefer confirmed open
    note = f"open until {_clock(closes)}" if status == "open" else "call to confirm hours"
    return s, d, note


def _clock(hhmm: str) -> str:
    hour, minute = int(hhmm[:2]), hhmm[3:]
    return f"{hour % 12 or 12}{':' + minute if minute != '00' else ''} {'am' if hour < 12 else 'pm'}"


def heat_reason(alert_name: str, spaces: list[CoolSpace], lon: float, lat: float, when: datetime,
                collected_at: str | None) -> Reason:
    hit = nearest_open(spaces, lon, lat, when)
    if hit is None:
        text = (f"Environment Canada {alert_name} in effect. No City cool space within "
                f"{SEARCH_M // 1000} km is open at this time")
    else:
        space, d, note = hit
        text = (f"Environment Canada {alert_name} in effect. Nearest cool space: {space.name} "
                f"({space.kind.lower()}), about {d:,.0f} m away, {note}")
    return Reason("alert", text, "toronto_cool_spaces", value=round(hit[1]) if hit else None,
                  as_of=when.date().isoformat(), collected_at=collected_at)
