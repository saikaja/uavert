"""The optional `hour` on street-level endpoints: picks that hour's stored crime score and explains it."""

import json

from uavert.api.live import LiveContext
from uavert.scoring.combine import Reason

CURRENT_CONDITIONS_NOTE = "Air quality, alerts and news show current conditions."


def hour_label(hour: int) -> str:
    return f"{hour % 12 or 12} {'am' if hour < 12 else 'pm'}"


def time_info(hour: int | None) -> dict:
    if hour is None:
        return {"hour": None, "label": "All day", "note": CURRENT_CONDITIONS_NOTE}
    return {"hour": hour, "label": hour_label(hour),
            "window": f"{hour_label((hour - 1) % 24)}-{hour_label((hour + 2) % 24)}", "note": CURRENT_CONDITIONS_NOTE}


def crime_at(row, hour: int | None, ctx: LiveContext) -> tuple[int, list[dict]]:
    """(crime score, crime reasons) for a street cell row, for the whole day or one hour."""
    reasons = _reasons(row)
    by_hour, intensity = row["crime_score_by_hour"], row["intensity_by_hour"]
    if hour is None or by_hour is None:
        return row["crime_score"], reasons
    factor, basis = ctx.activity[hour] if ctx.activity else (1.0, "estimated")
    how = "City pedestrian counts" if basis == "measured" else "estimated from Bike Share trips"
    dates = ctx.sources.get("activity_profile", {})
    reason = Reason(
        "crime",
        f"At {hour_label(hour)}: incidents near here run at about {intensity[hour]:.1f}× this block's average, "
        + (f"and foot traffic is about {factor:.1f}× the daytime average ({how})" if factor >= 0.95
           else f"and about {factor * 100:.0f}% of daytime foot traffic is out ({how})"),
        "activity_profile", value=round(intensity[hour], 2), as_of=dates.get("as_of"),
        collected_at=dates.get("collected_at"),
    ).to_dict()
    return by_hour[hour], [reason] + reasons


def _reasons(row) -> list[dict]:
    return json.loads(row["reasons"])
