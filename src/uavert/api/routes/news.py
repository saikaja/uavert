from datetime import timedelta

from fastapi import APIRouter, Query, Request

from uavert.api import live

router = APIRouter(tags=["news"])


@router.get("/news-events", summary="Recent news reports labelled as protests or violent incidents (unverified)")
async def news_events(request: Request, since_hours: int = Query(24, ge=1, le=168), limit: int = Query(50, ge=1, le=100)):
    pool = request.app.state.pool
    ctx = await live.load(pool)
    rows = await pool.fetch(
        "SELECT id, headline, url, publisher, source_key, category, location_text, published_at, collected_at,"
        " ST_X(geom) AS lon, ST_Y(geom) AS lat FROM news_events WHERE published_at > $1"
        " ORDER BY published_at DESC LIMIT $2",
        ctx.now - timedelta(hours=since_hours), limit,
    )
    return live.envelope([
        {"id": r["id"], "headline": r["headline"], "url": r["url"], "publisher": r["publisher"],
         "source_key": r["source_key"], "category": r["category"], "location_text": r["location_text"],
         "lat": r["lat"], "lon": r["lon"], "citywide": r["lon"] is None, "verified": False,
         "published_at": r["published_at"].isoformat(), "collected_at": r["collected_at"].isoformat()}
        for r in rows
    ], ctx)
