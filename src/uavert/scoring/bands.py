"""Risk bands: the one place band names and boundaries are defined. No band is ever "safe"."""

BANDS = (("lower", 0), ("moderate", 25), ("elevated", 50), ("high", 75))
BAND_LABELS = {
    "lower": "Lower reported risk",
    "moderate": "Moderate risk",
    "elevated": "Elevated risk",
    "high": "High risk",
}


def band_for(score: float) -> str:
    name = BANDS[0][0]
    for band, floor in BANDS:
        if score >= floor:
            name = band
    return name


def clamp_score(value: float) -> int:
    return max(0, min(100, round(value)))
