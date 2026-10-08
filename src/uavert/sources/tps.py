"""Toronto Police Service open data: incident datasets and neighbourhood crime rates.

Dates arrive as epoch milliseconds in UTC. Incident locations are offset by Toronto Police
to the nearest intersection; a latitude of 0 means no location was published.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from shapely.geometry import MultiPolygon, shape

BASE = "https://services.arcgis.com/S9th0jAJ7bqgIRjw/arcgis/rest/services"
LAYERS = {
    "tps_mci": f"{BASE}/Major_Crime_Indicators_Open_Data/FeatureServer/0",
    "tps_shootings": f"{BASE}/Shooting_and_Firearm_Discharges_Open_Data/FeatureServer/0",
    "tps_homicides": f"{BASE}/Homicides_Open_Data_ASR_RC_TBL_002/FeatureServer/0",
    "tps_ncr": f"{BASE}/Neighbourhood_Crime_Rates_Open_Data/FeatureServer/0",
}
INCIDENT_FIELDS = {
    "tps_mci": "EVENT_UNIQUE_ID,OCC_DATE,OCC_HOUR,PREMISES_TYPE,UCR_CODE,UCR_EXT,OFFENCE,HOOD_158,LAT_WGS84,LONG_WGS84",
    "tps_shootings": "EVENT_UNIQUE_ID,OCC_DATE,OCC_HOUR,EVENT_TYPE,HOOD_158,LAT_WGS84,LONG_WGS84",
    "tps_homicides": "EVENT_UNIQUE_ID,OCC_DATE,HOMICIDE_TYPE,HOOD_158,LAT_WGS84,LONG_WGS84",
}
# Published counts in the neighbourhood table that the incident datasets don't cover.
NCR_EXTRA_COUNTS = ("THEFTFROMMV", "BIKETHEFT")
NCR_ALL_COUNTS = ("ASSAULT", "AUTOTHEFT", "BIKETHEFT", "BREAKENTER", "HOMICIDE", "ROBBERY", "SHOOTING", "THEFTFROMMV", "THEFTOVER")


@dataclass(frozen=True)
class Incident:
    source_key: str
    event_id: str
    ucr_code: str
    ucr_ext: str
    offence: str
    premises_type: str | None
    occurred_at: datetime
    hood_external_id: str | None
    lon: float | None
    lat: float | None


@dataclass(frozen=True)
class NeighbourhoodRecord:
    external_id: str
    name: str
    population: int | None
    valid_year: int
    counts: dict[str, int]
    geom: MultiPolygon


def from_epoch_ms(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def hood_id(raw) -> str | None:
    """Normalise neighbourhood ids: '016' and 16 both become '16'; 'NSA' (not specified) becomes None."""
    if raw is None:
        return None
    raw = str(raw).strip()
    return str(int(raw)) if raw.isdigit() else None


def _location(a: dict) -> tuple[float | None, float | None]:
    lat, lon = a.get("LAT_WGS84"), a.get("LONG_WGS84")
    if not lat or not lon:
        return None, None
    return float(lon), float(lat)


def _occurred(a: dict) -> datetime:
    t = from_epoch_ms(a["OCC_DATE"])
    hour = a.get("OCC_HOUR")
    return t + timedelta(hours=int(hour)) if hour not in (None, "") else t


def parse_incident(source_key: str, a: dict) -> Incident:
    lon, lat = _location(a)
    if source_key == "tps_mci":
        code, ext, offence = a["UCR_CODE"], a["UCR_EXT"], a["OFFENCE"]
        premises = a.get("PREMISES_TYPE")
    elif source_key == "tps_shootings":
        code, ext, offence, premises = "*", "*", a.get("EVENT_TYPE") or "Shooting", None
    elif source_key == "tps_homicides":
        code, ext, premises = "*", "*", None
        offence = f"Homicide ({a.get('HOMICIDE_TYPE') or 'Other'})"
    else:
        raise ValueError(f"not an incident source: {source_key}")
    return Incident(
        source_key=source_key,
        event_id=a["EVENT_UNIQUE_ID"],
        ucr_code=str(code),
        ucr_ext=str(ext),
        offence=offence.strip(),
        premises_type=premises,
        occurred_at=_occurred(a),
        hood_external_id=hood_id(a.get("HOOD_158")),
        lon=lon,
        lat=lat,
    )


def parse_neighbourhood(feature: dict, year: int) -> NeighbourhoodRecord:
    p = feature["properties"]
    geom = shape(feature["geometry"])
    if geom.geom_type == "Polygon":
        geom = MultiPolygon([geom])
    return NeighbourhoodRecord(
        external_id=hood_id(p["HOOD_ID"]),
        name=p["AREA_NAME"].strip(),
        population=p.get(f"POPULATION_{year}"),
        valid_year=year,
        counts={k: int(p.get(f"{k}_{year}") or 0) for k in NCR_ALL_COUNTS},
        geom=geom,
    )


def ncr_fields(year: int) -> str:
    return ",".join(["AREA_NAME", "HOOD_ID", f"POPULATION_{year}"] + [f"{k}_{year}" for k in NCR_ALL_COUNTS])


@dataclass(frozen=True)
class CrimeYear:
    hood_external_id: str
    year: int
    offence: str  # Toronto Police field name, e.g. ASSAULT
    count: int
    rate_per_100k: float


def ncr_year_fields(first: int, last: int) -> str:
    return ",".join(f"{k}{s}_{y}" for y in range(first, last + 1) for k in NCR_ALL_COUNTS for s in ("", "_RATE"))


def parse_crime_years(p: dict, first: int, last: int) -> list[CrimeYear]:
    """Published yearly counts and rates per 100,000 residents (01-03-trends.md). A gap stops the load."""
    missing = [f for f in ncr_year_fields(first, last).split(",") if p.get(f) is None]
    if missing:
        raise ValueError(f"neighbourhood {p.get('HOOD_ID')}: no published figure for {', '.join(missing[:5])}")
    hood = hood_id(p["HOOD_ID"])
    return [CrimeYear(hood, y, k, int(p[f"{k}_{y}"]), float(p[f"{k}_RATE_{y}"]))
            for y in range(first, last + 1) for k in NCR_ALL_COUNTS]
