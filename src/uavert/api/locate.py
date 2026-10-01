"""Turning a request's address or coordinates into a scored place."""

import json

import asyncpg
from fastapi import Request

from uavert.api.errors import ApiError
from uavert.api.live import LiveContext
from uavert.config import get_settings
from uavert.sources.geocode import Geocoder, Place, parse_latlon
from uavert.sources.http import SourceUnavailable, make_client
from uavert.sources.routing import Router


def _http(state):
    if getattr(state, "http", None) is None:
        state.http = make_client()
    return state.http


def geocoder(request: Request) -> Geocoder:
    state = request.app.state
    if getattr(state, "geocoder", None) is None:
        state.geocoder = Geocoder(_http(state), get_settings().nominatim_url)
    return state.geocoder


def walking_router(request: Request) -> Router:
    state = request.app.state
    if getattr(state, "router", None) is None:
        state.router = Router(_http(state), get_settings().osrm_url)
    return state.router


async def resolve(request: Request, text: str) -> Place:
    """An address or 'lat,lon' -> Place. 404 when not found, 502 when the address service is down."""
    place = parse_latlon(text)
    if place:
        return place
    try:
        place = await geocoder(request).search(text)
    except SourceUnavailable:
        raise ApiError(502, "upstream_unavailable", "The address search service isn't responding. Try again shortly.")
    if place is None:
        raise ApiError(404, "address_not_found", f"We couldn't find \"{text}\". Try adding a street number or 'Toronto'.")
    return place


async def neighbourhood_at(pool: asyncpg.Pool, place: Place) -> asyncpg.Record:
    """The neighbourhood containing the place; 422 outside_coverage when it's outside Toronto."""
    row = await pool.fetchrow(
        "SELECT n.id, n.name, ST_X(ST_PointOnSurface(n.geom)) AS lon, ST_Y(ST_PointOnSurface(n.geom)) AS lat,"
        " s.crime_score, s.reasons FROM neighbourhoods n JOIN neighbourhood_scores s ON s.neighbourhood_id = n.id"
        " WHERE ST_Covers(n.geom, ST_SetSRID(ST_MakePoint($1, $2), 4326)) LIMIT 1",
        place.lon, place.lat,
    )
    if row is None:
        raise ApiError(422, "outside_coverage", f"{place.display_name} is outside the area we cover. Uavert currently covers the City of Toronto.")
    return row


async def score_place(pool: asyncpg.Pool, ctx: LiveContext, place: Place) -> dict:
    hood = await neighbourhood_at(pool, place)
    cell = await pool.fetchrow(
        "SELECT c.h3::text AS h3, s.crime_score, s.incident_count, s.reasons FROM cell_scores s"
        " JOIN cells c ON c.h3 = s.h3 WHERE s.h3 = h3_lat_lng_to_cell(point($1, $2), 9)",
        place.lon, place.lat,
    )
    hood_score = ctx.score(hood["lon"], hood["lat"], hood["crime_score"], json.loads(hood["reasons"]),
                           neighbourhood_id=hood["id"])
    if cell:  # the street cell; at the city edge a point can fall in a cell whose centre is outside Toronto
        street = {"h3": cell["h3"], "incident_count": cell["incident_count"],
                  **ctx.score(place.lon, place.lat, cell["crime_score"], json.loads(cell["reasons"]),
                              cell=cell["h3"]).to_dict()}
    else:
        street = {"h3": None, "incident_count": None,
                  **ctx.score(place.lon, place.lat, hood["crime_score"], json.loads(hood["reasons"]),
                              neighbourhood_id=hood["id"]).to_dict()}
    return {
        "location": {"display_name": place.display_name, "lon": place.lon, "lat": place.lat},
        "street": street,
        "neighbourhood": {"id": hood["id"], "name": hood["name"], **hood_score.to_dict()},
    }
