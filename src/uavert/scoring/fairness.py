"""Fairness check from the build plan: if neighbourhood scores mostly track income rather than crime,
the weights should be reviewed. Measured with Spearman rank correlation."""

from collections.abc import Sequence

REVIEW_THRESHOLD = 0.5  # |rho| at or above this counts as "mostly follows"
OK_LABEL = "Scores don't mostly follow income"
REVIEW_LABEL = "Review the weights: scores follow income closely"


def ranks(values: Sequence[float]) -> list[float]:
    """1-based ranks; ties share the average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Rank correlation from -1 to 1; None when it can't be computed (fewer than 3 pairs, or no spread)."""
    if len(x) != len(y) or len(x) < 3:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx, vy = sum((a - mx) ** 2 for a in rx), sum((b - my) ** 2 for b in ry)
    return cov / (vx * vy) ** 0.5 if vx and vy else None


def label(rho_income: float | None, rho_low_income: float | None) -> str:
    strongest = max((abs(r) for r in (rho_income, rho_low_income) if r is not None), default=0.0)
    return REVIEW_LABEL if strongest >= REVIEW_THRESHOLD else OK_LABEL
