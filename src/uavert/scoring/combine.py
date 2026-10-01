"""Combining category scores: the highest one wins, so one serious risk is never averaged away."""

from dataclasses import asdict, dataclass, field

from uavert.scoring.bands import band_for, clamp_score

CATEGORIES = ("crime", "environment", "alert", "news")
MAX_REASONS = 3
MAX_REASONS_PER_CATEGORY = 2


@dataclass
class Reason:
    category: str
    text: str
    source_key: str
    value: float | int | str | None = None
    as_of: str | None = None  # date the underlying data refers to
    collected_at: str | None = None  # when we collected it
    url: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None or k in ("as_of", "collected_at")}


@dataclass
class Score:
    score: int
    band: str
    categories: dict[str, int]
    reasons: list[Reason] = field(default_factory=list)

    def to_dict(self, with_reasons: bool = True) -> dict:
        out = {"score": self.score, "band": self.band, "categories": self.categories}
        if with_reasons:
            out["reasons"] = [r.to_dict() for r in self.reasons]
        return out


def combine(categories: dict[str, float], reasons: list[Reason]) -> Score:
    cats = {c: clamp_score(categories.get(c, 0)) for c in CATEGORIES}
    score = max(cats.values())
    picked: list[Reason] = []
    for cat in sorted(CATEGORIES, key=lambda c: -cats[c]):
        picked += [r for r in reasons if r.category == cat][:MAX_REASONS_PER_CATEGORY]
    return Score(score=score, band=band_for(score), categories=cats, reasons=picked[:MAX_REASONS])
