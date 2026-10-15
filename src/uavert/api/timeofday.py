"""The optional `hour` on street-level endpoints: picks that hour's stored crime score and explains it."""

import json

from uavert.api.live import TORONTO_TZ, LiveContext
from uavert.scoring.combine import Reason

CURRENT_CONDITIONS_NOTE = "Air quality, alerts and news show current conditions."


def hour_label(hour: int) -> str:
    return f"{hour % 12 or 12} {'am' if hour < 12 else 'pm'}"


def moment(hour: int | None, ctx: LiveContext):
    """The Toronto local time scores are checked at: today at the chosen hour, or now."""
    local = ctx.now.astimezone(TORONTO_TZ)
    return local if hour is None else local.replace(hour=hour, minute=0, second=0, microsecond=0)


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
    reason = _hour_reason(
        f"At {hour_label(hour)}: incidents near here run at about {intensity[hour]:.1f}× this block's average, and ",
        round(intensity[hour], 2), hour, ctx)
    return by_hour[hour], [reason] + reasons


def neighbourhood_crime_at(row, hour: int | None, ctx: LiveContext) -> tuple[int, list[dict]]:
    """(crime score, crime reasons) for a neighbourhood row, for the whole day or one hour (01-03-time-map.md)."""
    reasons = _reasons(row)
    by_hour, moves = row["crime_score_by_hour"], row["move_by_hour"]
    if hour is None or by_hour is None:
        return row["crime_score"], reasons
    move = round(moves[hour])
    change = (f"about {move} points higher than" if move >= 3 else f"about {-move} points lower than" if move <= -3
              else "about the same as")
    reason = _hour_reason(f"At {hour_label(hour)}: street blocks here typically score {change} all day, and ",
                          move, hour, ctx)
    return by_hour[hour], [reason] + reasons


def _hour_reason(start: str, value, hour: int, ctx: LiveContext) -> dict:
    """A reason for a score at an hour, ending with how many people are out then and where that figure comes from."""
    factor, basis = ctx.activity[hour] if ctx.activity else (1.0, "estimated")
    how = "City pedestrian counts" if basis == "measured" else "estimated from Bike Share trips"
    dates = ctx.sources.get("activity_profile", {})
    return Reason(
        "crime",
        start + (f"foot traffic is about {factor:.1f}× the daytime average ({how})" if factor >= 0.95
                 else f"about {factor * 100:.0f}% of daytime foot traffic is out ({how})"),
        "activity_profile", value=value, as_of=dates.get("as_of"), collected_at=dates.get("collected_at"),
    ).to_dict()


def _reasons(row) -> list[dict]:
    return json.loads(row["reasons"])
