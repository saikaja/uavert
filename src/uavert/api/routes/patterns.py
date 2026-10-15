import asyncpg
from fastapi import APIRouter, Request

from uavert.api import live
from uavert.scoring.patterns import OFFENCES, USUAL_FLOOR

router = APIRouter(tags=["news"])


async def pattern_rows(pool: asyncpg.Pool, neighbourhood_id: int | None = None) -> list[dict]:
    """Patterns in police reports (01-03-news.md), most unusual first. Information only; never scored."""
    rows = await pool.fetch(
        "SELECT p.neighbourhood_id, n.name, p.offence, p.recent, p.usual_per_30_days, p.chance, p.first_date, p.last_date,"
        " p.computed_at FROM crime_patterns p JOIN neighbourhoods n ON n.id = p.neighbourhood_id"
        " WHERE $1::int IS NULL OR p.neighbourhood_id = $1 ORDER BY p.chance", neighbourhood_id)
    return [{"neighbourhood_id": r["neighbourhood_id"], "neighbourhood": r["name"], "offence": r["offence"],
             "offence_label": OFFENCES.get(r["offence"], r["offence"]), "recent": r["recent"],
             "usual_per_30_days": round(r["usual_per_30_days"], 1),
             "times_usual": round(r["recent"] / max(r["usual_per_30_days"], USUAL_FLOOR), 1),
             "first_date": r["first_date"].isoformat(), "last_date": r["last_date"].isoformat(),
             "data_as_of": r["last_date"].isoformat(), "source_key": "tps_mci",
             "computed_at": r["computed_at"].isoformat()} for r in rows]


@router.get("/crime-patterns", summary="Neighbourhoods where break-ins or auto thefts ran well above their usual level"
                                       " in the latest 30 days of police data (information only)")
async def crime_patterns(request: Request):
    pool = request.app.state.pool
    ctx = await live.load(pool)
    return live.envelope(await pattern_rows(pool), ctx)
