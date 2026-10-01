"""Official alert score from Environment Canada's risk colour: yellow moderate, orange elevated, red high;
without a colour, warnings are elevated and watches and advisories moderate; statements are information only."""

from dataclasses import dataclass
from datetime import datetime

from uavert.scoring.combine import Reason

TOP_BAND_SCORE = 90
ADVISORY_SCORE = 25


@dataclass(frozen=True)
class Alert:
    name: str
    alert_type: str
    risk_colour: str | None
    status: str
    issued_at: datetime
    expires_at: datetime | None
    collected_at: str | None = None


def is_active(a: Alert, now: datetime) -> bool:
    return a.status != "ended" and (a.expires_at is None or a.expires_at > now)


COLOUR_SCORES = {"yellow": 40, "orange": 65, "red": TOP_BAND_SCORE}  # Environment Canada's own risk colours
WARNING_WITHOUT_COLOUR = 65


def alert_level(a: Alert) -> int:
    """Use Environment Canada's colour when it gives one; otherwise fall back on the alert type."""
    colour = (a.risk_colour or "").lower()
    if colour in COLOUR_SCORES and a.alert_type != "statement":
        return COLOUR_SCORES[colour]
    if a.alert_type == "warning":
        return WARNING_WITHOUT_COLOUR
    if a.alert_type in ("watch", "advisory"):
        return ADVISORY_SCORE
    return 0


def alert_score(covering: list[Alert], now: datetime) -> tuple[int, list[Reason]]:
    active = sorted((a for a in covering if is_active(a, now)), key=alert_level, reverse=True)
    reasons = [
        Reason("alert", f"Environment Canada {a.name} in effect"
               + (f" until {a.expires_at:%Y-%m-%d %H:%M} UTC" if a.expires_at else ""),
               "eccc_alerts", value=a.alert_type, as_of=a.issued_at.isoformat(), collected_at=a.collected_at)
        for a in active
    ]
    return (alert_level(active[0]) if active else 0), reasons
