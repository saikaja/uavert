"""Write a report comparing neighbourhood rankings: the September demo's weights vs StatCan CSI weights.

Usage: python scripts/compare_rankings.py <output.md>
Reads stored data only (run `uavert ingest reference`, `uavert ingest crime`, `uavert build-scores` first).
"""

import asyncio
import json
import sys
from datetime import datetime

from uavert import db
from uavert.scoring.crime import percentile_scores

# The demo (September 29, 2026) weighted Toronto Police's published 2025 rates per 100,000.
DEMO_WEIGHTS = {"HOMICIDE": 10, "SHOOTING": 5, "ASSAULT": 3, "ROBBERY": 3, "BREAKENTER": 2,
                "AUTOTHEFT": 1, "THEFTOVER": 1, "THEFTFROMMV": 1, "BIKETHEFT": 0.5}


def band(s: int) -> str:
    return "lower" if s < 25 else "moderate" if s < 50 else "elevated" if s < 75 else "high"


async def main(out_path: str) -> None:
    conn = await db.connect()
    rows = await conn.fetch(
        "SELECT n.id, n.name, n.population, n.counts, s.crime_score, s.weighted_rate, s.computed_at"
        " FROM neighbourhoods n JOIN neighbourhood_scores s ON s.neighbourhood_id = n.id"
    )
    collected = await conn.fetchval("SELECT last_collected_at FROM sources WHERE key = 'tps_mci'")
    await conn.close()

    demo_rate = {r["id"]: sum(json.loads(r["counts"]).get(k, 0) / r["population"] * 100_000 * w
                              for k, w in DEMO_WEIGHTS.items()) for r in rows}
    demo = percentile_scores(demo_rate)
    by_id = {r["id"]: r for r in rows}
    demo_rank = {i: n for n, i in enumerate(sorted(demo, key=lambda i: -demo_rate[i]), 1)}
    csi_rank = {i: n for n, i in enumerate(sorted(by_id, key=lambda i: -by_id[i]["weighted_rate"]), 1)}

    def table(ids, cols):
        lines = ["| " + " | ".join(h for h, _ in cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(str(f(i)) for _, f in cols) + " |" for i in ids]
        return "\n".join(lines)

    cols = [("Neighbourhood", lambda i: by_id[i]["name"]),
            ("Demo rank", lambda i: demo_rank[i]), ("Demo score", lambda i: f"{demo[i]} ({band(demo[i])})"),
            ("CSI rank", lambda i: csi_rank[i]), ("CSI score", lambda i: f"{by_id[i]['crime_score']} ({band(by_id[i]['crime_score'])})"),
            ("Change", lambda i: f"{demo_rank[i] - csi_rank[i]:+d}")]
    moved = sorted(by_id, key=lambda i: -abs(demo_rank[i] - csi_rank[i]))
    band_changes = sum(band(demo[i]) != band(by_id[i]["crime_score"]) for i in by_id)
    computed = max(r["computed_at"] for r in rows)

    report = f"""# Neighbourhood ranking: demo weights vs StatCan CSI weights

*Generated {datetime.now():%Y-%m-%d %H:%M}. Scores computed {computed:%Y-%m-%d %H:%M %Z}; Toronto Police data collected {collected:%Y-%m-%d %H:%M %Z}.*

## How the two are calculated

- **Demo (September 29, 2026):** Toronto Police's published 2025 rates per 100,000, weighted by hand: homicide 10, shootings 5, assault 3, robbery 3, break and enter 2, auto theft 1, theft over $5,000 1, theft from vehicles 1, bicycle theft 0.5.
- **CSI (this build):** every 2025 incident weighted by its Statistics Canada Crime Severity Index weight (2009 published table): murder 7,042, discharging a firearm 988, robbery 583, aggravated assault 405, break and enter 187, theft over $5,000 139, auto theft 84, assault with a weapon 77, common assault 23, thefts under $5,000 37. Each event is counted once across the Toronto Police datasets, and homicides use the 2023-2025 average (3 years) so a single homicide doesn't swing a small neighbourhood.

Both are ranked across the 158 neighbourhoods (0 = lowest, 100 = highest).

## Summary

- **{band_changes} of 158 neighbourhoods change band.**
- **Biggest shift:** under CSI, common assault counts for much less (23 against robbery's 583), and homicides and shootings count for much more. Areas with many assaults but few robberies, shootings or homicides drop; areas with robberies, shootings or homicides rise.

## Top 15 under CSI

{table(sorted(by_id, key=lambda i: csi_rank[i])[:15], cols)}

## Top 15 under the demo weights

{table(sorted(by_id, key=lambda i: demo_rank[i])[:15], cols)}

## 15 biggest movers

Positive change = ranks riskier under CSI.

{table(moved[:15], cols)}

## Lowest 10 under CSI

{table(sorted(by_id, key=lambda i: csi_rank[i])[-10:], cols)}
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Wrote {out_path}: {band_changes} neighbourhoods change band")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
