"""City of Toronto Open Data (CKAN): intersection traffic counts (Turning Movement Counts)."""

import csv
import io
import json
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


COOL_PACKAGE = "air-conditioned-and-cool-spaces-heat-relief-network"
COOL_CSV = "Air Conditioned and Cool Spaces - 4326.csv"
_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True)
class CoolSpaceRecord:
    location_id: str
    name: str
    kind: str
    address: str | None
    hours: dict
    notes: str | None
    lon: float
    lat: float


def _hours(row: dict, day: str):
    opens, closes = (row.get(f"{day}Open") or "").strip(), (row.get(f"{day}Close") or "").strip()
    if opens.upper() == "CALL" or closes.upper() == "CALL":
        return "call"
    if opens.isdigit() and closes.isdigit() and len(opens) == len(closes) == 4:
        return [opens, closes]
    return None


def parse_cool_spaces(text: str) -> list[CoolSpaceRecord]:
    out = []
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        try:
            lon, lat = json.loads(r["geometry"])["coordinates"][0]
        except (KeyError, ValueError, IndexError, TypeError):
            continue
        none = lambda v: None if v in (None, "", "None") else v.strip()  # noqa: E731
        out.append(CoolSpaceRecord(r["locationId"], r["locationName"].strip(), r["locationTypeDesc"].strip(),
                                   none(r.get("address")), {d: _hours(r, d) for d in _DAYS}, none(r.get("notes")),
                                   float(lon), float(lat)))
    return out


async def fetch_cool_spaces(client: httpx.AsyncClient) -> list[CoolSpaceRecord]:
    r = await get(client, await resource_url(client, COOL_PACKAGE, COOL_CSV))
    return parse_cool_spaces(r.text)


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
