"""City of Toronto Open Data (CKAN): intersection traffic counts (Turning Movement Counts)."""

import csv
import io
from dataclasses import dataclass
from datetime import date

import httpx

from uavert.sources.http import SourceUnavailable, get, get_json

CKAN = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"
TMC_PACKAGE = "traffic-volumes-at-intersections-for-all-modes"
TMC_RECENT = "tmc_most_recent_summary_data.csv"


@dataclass(frozen=True)
class TrafficCount:
    location_key: str
    location_name: str
    count_id: str
    count_date: date
    hours: float
    pedestrians: int
    bikes: int
    vehicles: int
    lon: float
    lat: float

    @property
    def pedestrians_per_hour(self) -> float:
        return self.pedestrians / self.hours


def _int(v: str) -> int:
    return int(float(v)) if v not in ("", None) else 0


def parse_tmc_csv(text: str) -> list[TrafficCount]:
    """One count per location (the most recent). Rows without coordinates are skipped.
    count_duration is '14' for a 14-hour count, '8R' or '8S' for the older 8-hour counts."""
    out: dict[str, TrafficCount] = {}
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        if not r.get("latitude") or not r.get("longitude"):
            continue
        key = f"{r['centreline_type']}:{r['centreline_id']}" if r.get("centreline_id") else f"name:{r['location_name']}"
        c = TrafficCount(
            location_key=key,
            location_name=r["location_name"].strip(),
            count_id=r["latest_count_id"],
            count_date=date.fromisoformat(r["latest_count_date"][:10]),
            hours=14.0 if r["count_duration"].strip() == "14" else 8.0,
            pedestrians=_int(r["total_pedestrian"]),
            bikes=_int(r["total_bike"]),
            vehicles=_int(r["total_vehicle"]),
            lon=float(r["longitude"]),
            lat=float(r["latitude"]),
        )
        if key not in out or c.count_date > out[key].count_date:
            out[key] = c
    return list(out.values())


async def resource_url(client: httpx.AsyncClient, package: str, resource_name: str) -> str:
    """Look the file up by name, so the loader keeps working if the City moves it."""
    data = await get_json(client, f"{CKAN}/package_show", {"id": package})
    for r in data.get("result", {}).get("resources", []):
        if r.get("name") == resource_name:
            return r["url"]
    raise SourceUnavailable(f"{package}: no resource named {resource_name}")


async def fetch_tmc(client: httpx.AsyncClient) -> list[TrafficCount]:
    r = await get(client, await resource_url(client, TMC_PACKAGE, TMC_RECENT))
    try:
        return parse_tmc_csv(r.text)
    except (KeyError, ValueError) as e:
        raise SourceUnavailable(f"{TMC_RECENT} could not be read: {e}") from e
