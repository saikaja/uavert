import json
import math

from fastapi import APIRouter, Query, Request

from uavert.api import live
from uavert.api.errors import ApiError
from uavert.api.locate import street_extras

router = APIRouter(tags=["street cells"])

MAX_BBOX_KM2 = 25.0  # about 2,500 cells


def parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    try:
        min_lon, min_lat, max_lon, max_lat = (float(v) for v in bbox.split(","))
    except ValueError:
        raise ApiError(422, "invalid_bbox", "bbox must be four numbers: minLon,minLat,maxLon,maxLat.")
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise ApiError(422, "invalid_bbox", "bbox must be minLon,minLat,maxLon,maxLat with min values below max values.")
    km2 = (max_lon - min_lon) * 111.32 * math.cos(math.radians((min_lat + max_lat) / 2)) * (max_lat - min_lat) * 110.57
    if km2 > MAX_BBOX_KM2:
        raise ApiError(422, "bbox_too_large", f"The area requested is about {km2:,.0f} km²; the limit is {MAX_BBOX_KM2:.0f} km². Zoom in.")
    return min_lon, min_lat, max_lon, max_lat


@router.get("/cells", summary="Street-level cells (H3, about one city block) in a map area, as GeoJSON")
async def list_cells(request: Request, bbox: str = Query(description="minLon,minLat,maxLon,maxLat", max_length=200)):
    box = parse_bbox(bbox)
    pool = request.app.state.pool
    ctx = await live.load(pool)
    rows = await pool.fetch(
        "SELECT c.h3::text AS h3, ST_AsGeoJSON(c.geom, 6) AS g, ST_X(c.centre) AS lon, ST_Y(c.centre) AS lat,"
        " s.crime_score, s.incident_count, s.reasons, s.foot_traffic_per_hour, s.vs_surroundings, s.busy_area"
        " FROM cells c JOIN cell_scores s ON s.h3 = c.h3"
        " WHERE c.geom && ST_MakeEnvelope($1, $2, $3, $4, 4326)",
        *box,
    )
    features = []
    for r in rows:
        score = ctx.score(r["lon"], r["lat"], r["crime_score"], json.loads(r["reasons"]), cell=r["h3"])
        features.append({
            "type": "Feature", "geometry": json.loads(r["g"]),
            "properties": {"h3": r["h3"], "incident_count": r["incident_count"], **street_extras(r),
                           "top_reason": score.reasons[0].text if score.reasons else None,
                           **score.to_dict(with_reasons=False)},
        })
    return live.envelope({"type": "FeatureCollection", "features": features}, ctx)
