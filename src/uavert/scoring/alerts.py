"""Official alert score. Warnings (and any orange or red alert) put an area in the top band;
watches and advisories set a moderate floor; statements are listed for information only."""

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


def alert_level(a: Alert) -> int:
    if a.alert_type == "warning" or (a.risk_colour or "").lower() in ("orange", "red"):
        return TOP_BAND_SCORE
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
