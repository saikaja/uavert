from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Query, Request

from uavert.api import live
from uavert.scoring import trending as trending_rules
from uavert.scoring.news import DISPLAY_DAYS

router = APIRouter(tags=["news"])

_COLUMNS = ("SELECT id, headline, url, publisher, source_key, category, location_text, published_at, collected_at,"
            " ST_X(geom) AS lon, ST_Y(geom) AS lat FROM news_events")


def _item(r) -> dict:
    return {"id": r["id"], "headline": r["headline"], "url": r["url"], "publisher": r["publisher"],
            "source_key": r["source_key"], "category": r["category"], "location_text": r["location_text"],
            "lat": r["lat"], "lon": r["lon"], "citywide": r["lon"] is None, "verified": False,
            "published_at": r["published_at"].isoformat(), "collected_at": r["collected_at"].isoformat(),
            "window_days": DISPLAY_DAYS[r["category"]]}


@router.get("/news-events", summary="Recent news reports labelled by type of event (unverified)")
async def news_events(request: Request, since_hours: int = Query(24, ge=1, le=168), limit: int = Query(50, ge=1, le=100),
                      window: Literal["by_type"] | None = Query(
                          None, description="by_type: each type for its own window (protests 2 days, violent incidents"
                                            " 7 days, property crime 60 days); since_hours is then ignored")):
    pool = request.app.state.pool
    ctx = await live.load(pool)
    if window == "by_type":
        rows = [r for category, days in DISPLAY_DAYS.items() for r in await pool.fetch(
            f"{_COLUMNS} WHERE category = $1 AND published_at > $2 ORDER BY published_at DESC LIMIT $3",
            category, ctx.now - timedelta(days=days), limit)]
    else:
        rows = await pool.fetch(f"{_COLUMNS} WHERE published_at > $1 ORDER BY published_at DESC LIMIT $2",
                                ctx.now - timedelta(hours=since_hours), limit)
    return live.envelope([_item(r) for r in rows], ctx)


@router.get("/news-trending", summary="Stories about the same event from several outlets in the last 3 days (unverified)")
async def news_trending(request: Request):
    pool = request.app.state.pool
    ctx = await live.load(pool)
    rows = await pool.fetch(
        "SELECT headline, url, publisher, category, published_at FROM news_events WHERE published_at > $1",
        ctx.now - timedelta(days=7))
    stories = [trending_rules.Story(r["headline"], r["url"], r["publisher"], r["category"], r["published_at"]) for r in rows]
    return live.envelope(trending_rules.trending(stories, ctx.now), ctx)
