import json

from fastapi import APIRouter, Depends, Query, Request

from uavert.api import live
from uavert.api.errors import ApiError
from uavert.api.locate import neighbourhood_at, resolve, score_place, walking_router
from uavert.api.ratelimit import limit_outside_calls
from uavert.scoring import route as route_rules
from uavert.sources.http import SourceUnavailable
from uavert.sources.routing import NoRoute

router = APIRouter(tags=["destination and route"])

MAX_ROUTE_M = 10_000
SAME_PLACE_M = 25


def _line(points):
    return {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in points]}


@router.get(
    "/route-risks",
    summary="Where I'm walking: the risk score for a walking route and its riskiest stretches",
    dependencies=[Depends(limit_outside_calls)],
)
async def route_risks(
    request: Request,
    from_: str = Query(alias="from", min_length=3, max_length=200, description="Start: an address or 'lat,lon'"),
    to: str = Query(min_length=3, max_length=200, description="End: an address or 'lat,lon'"),
):
    start, end = await resolve(request, from_), await resolve(request, to)
    pool = request.app.state.pool
    for place in (start, end):
        await neighbourhood_at(pool, place)  # 422 outside_coverage
    straight = route_rules.distance_m((start.lon, start.lat), (end.lon, end.lat))
    if straight > MAX_ROUTE_M:
        raise ApiError(422, "route_too_long", f"Those places are {straight / 1000:.1f} km apart; walking routes are limited to {MAX_ROUTE_M // 1000} km.")
    ctx = await live.load(pool)
    if straight < SAME_PLACE_M:
        here = await score_place(pool, ctx, end)
        return live.envelope({"from": {"query": from_, "display_name": start.display_name}, "to": {"query": to, "display_name": end.display_name},
                              "distance_m": 0, "duration_s": 0, "geometry": _line([(end.lon, end.lat)]),
                              **{k: here["street"][k] for k in ("score", "band", "categories", "reasons")},
                              "riskiest_segments": []}, ctx)
    try:
        walk = await walking_router(request).walk(start, end)
    except NoRoute:
        raise ApiError(422, "no_route", "We couldn't find a walking route between those places.")
    except SourceUnavailable:
        raise ApiError(502, "upstream_unavailable", "The walking-route service isn't responding. Try again shortly.")
    if walk.distance_m > MAX_ROUTE_M:
        raise ApiError(422, "route_too_long", f"That walk is {walk.distance_m / 1000:.1f} km; walking routes are limited to {MAX_ROUTE_M // 1000} km.")

    points = route_rules.densify(walk.coordinates)
    cells = sorted({route_rules.cell_of(p) for p in points})
    rows = await pool.fetch(
        "SELECT c.h3::text AS h3, ST_X(c.centre) AS lon, ST_Y(c.centre) AS lat, s.crime_score, s.reasons"
        " FROM cells c JOIN cell_scores s ON s.h3 = c.h3 WHERE c.h3 = ANY($1::text[]::h3index[])",
        cells,
    )
    scored = {r["h3"]: ctx.score(r["lon"], r["lat"], r["crime_score"], json.loads(r["reasons"]), cell=r["h3"])
              for r in rows}
    if not scored:
        raise ApiError(422, "outside_coverage", "That route doesn't pass through the area we cover.")
    worst = max(scored.values(), key=lambda s: s.score)
    runs = route_rules.stretches(points, {c: s.score for c, s in scored.items()})
    segments = [{"geometry": _line(r.points), "length_m": round(r.length_m), "score": r.score, "band": r.band,
                 "reasons": [x.to_dict() for x in scored[r.worst_cell].reasons]} for r in route_rules.riskiest(runs)]
    return live.envelope({
        "from": {"query": from_, "display_name": start.display_name, "lon": start.lon, "lat": start.lat},
        "to": {"query": to, "display_name": end.display_name, "lon": end.lon, "lat": end.lat},
        "distance_m": round(walk.distance_m), "duration_s": round(walk.duration_s),
        "geometry": _line(walk.coordinates),
        **worst.to_dict(),
        "cells_scored": len(scored),
        "riskiest_segments": segments,
    }, ctx)
