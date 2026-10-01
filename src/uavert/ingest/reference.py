"""Reference data: CSI weights, the offence map, neighbourhoods and the H3 street grid."""

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import asyncpg
import httpx

from uavert.config import PROJECT_ROOT, get_settings
from uavert.ingest.runs import ingest_run
from uavert.sources import arcgis, tps

DATA_DIR = PROJECT_ROOT / "data"
NCR_YEAR = 2025
H3_RESOLUTION = 9


def read_csv(path: Path) -> list[dict]:
    """Read a CSV whose leading '#' lines describe where the data came from."""
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
    return list(csv.DictReader(lines))


@dataclass(frozen=True)
class OffenceMapping:
    source_key: str
    ucr_code: str
    ucr_ext: str
    offence_label: str
    csi_offence_key: str
    match: str
    group_label: str


class UnmappedOffence(Exception):
    pass


class OffenceMap:
    """Resolves a source offence to its CSI offence; exact codes win over '*' wildcards."""

    def __init__(self, rows: list[dict]):
        self._rows = {(r["source_key"], r["ucr_code"], r["ucr_ext"]): OffenceMapping(**{k: r[k] for k in OffenceMapping.__dataclass_fields__}) for r in rows}

    def resolve(self, source_key: str, code: str, ext: str) -> OffenceMapping | None:
        for key in ((source_key, code, ext), (source_key, code, "*"), (source_key, "*", "*")):
            if key in self._rows:
                return self._rows[key]
        return None

    def check(self, offences: set[tuple[str, str, str, str]]) -> None:
        """Raise UnmappedOffence naming every (source, code, ext, label) with no mapping."""
        missing = sorted(o for o in offences if self.resolve(o[0], o[1], o[2]) is None)
        if missing:
            listed = "; ".join(f"{s} {c}-{e} '{label}'" for s, c, e, label in missing)
            raise UnmappedOffence(f"No CSI mapping for {len(missing)} offence(s): {listed}. Add them to data/offence_map.csv.")

    def rows(self) -> list[OffenceMapping]:
        return list(self._rows.values())


def load_offence_map() -> OffenceMap:
    return OffenceMap(read_csv(DATA_DIR / "offence_map.csv"))


async def load_csi_and_offence_map(conn: asyncpg.Connection) -> int:
    weights = read_csv(DATA_DIR / "csi_weights.csv")
    edition = get_settings().csi_edition
    keys = {w["offence_key"] for w in weights if w["edition"] == edition}
    if not keys:
        raise ValueError(f"data/csi_weights.csv has no weights for edition {edition}")
    offence_map = load_offence_map()
    bad = {m.csi_offence_key for m in offence_map.rows()} - keys
    if bad:
        raise ValueError(f"offence_map.csv refers to CSI offences missing from edition {edition}: {sorted(bad)}")

    async with conn.transaction():
        for w in weights:
            await conn.execute(
                "INSERT INTO csi_weights (edition, offence_key, label, weight, source_url, retrieved_on)"
                " VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (edition, offence_key)"
                " DO UPDATE SET label = $3, weight = $4, source_url = $5, retrieved_on = $6",
                w["edition"], w["offence_key"], w["label"], float(w["weight"]), w["source_url"],
                datetime.strptime(w["retrieved_on"], "%Y-%m-%d").date(),
            )
        for m in offence_map.rows():
            await conn.execute(
                "INSERT INTO offence_map (source_key, ucr_code, ucr_ext, offence_label, csi_offence_key, match, group_label)"
                " VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (source_key, ucr_code, ucr_ext)"
                " DO UPDATE SET offence_label = $4, csi_offence_key = $5, match = $6, group_label = $7",
                m.source_key, m.ucr_code, m.ucr_ext, m.offence_label, m.csi_offence_key, m.match, m.group_label,
            )
    return len(weights) + len(offence_map.rows())


async def load_neighbourhoods(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> int:
    records = []
    async for page in arcgis.query_pages(
        client, tps.LAYERS["tps_ncr"], "1=1", tps.ncr_fields(NCR_YEAR), fmt="geojson", order_by=None
    ):
        records += [tps.parse_neighbourhood(f, NCR_YEAR) for f in page]
    if len(records) != 158:
        raise ValueError(f"expected 158 Toronto neighbourhoods, got {len(records)}")
    async with conn.transaction():
        for n in records:
            await conn.execute(
                "INSERT INTO neighbourhoods (region_id, external_id, name, population, valid_year, counts, geom)"
                " VALUES ($1, $2, $3, $4, $5, $6::jsonb, ST_Multi(ST_MakeValid(ST_GeomFromText($7, 4326))))"
                " ON CONFLICT (region_id, external_id) DO UPDATE SET name = $3, population = $4, valid_year = $5,"
                " counts = $6::jsonb, geom = EXCLUDED.geom, last_seen_at = now()",
                region_id, n.external_id, n.name, n.population, n.valid_year, json.dumps(n.counts), n.geom.wkt,
            )
    return len(records)


async def build_cells(conn: asyncpg.Connection, region_id: int) -> int:
    """Cover each neighbourhood with H3 cells; a cell belongs to the neighbourhood holding its centre."""
    await conn.execute(
        "INSERT INTO cells (h3, region_id, neighbourhood_id, geom, centre)"
        " SELECT c, n.region_id, n.id, h3_cell_to_boundary_geometry(c), h3_cell_to_geometry(c)"
        " FROM neighbourhoods n, LATERAL h3_polygon_to_cells(n.geom, $2) c"
        " WHERE n.region_id = $1 ON CONFLICT (h3) DO NOTHING",
        region_id, H3_RESOLUTION,
    )
    return await conn.fetchval("SELECT count(*) FROM cells WHERE region_id = $1", region_id)


async def run(conn: asyncpg.Connection, client: httpx.AsyncClient, region_id: int) -> None:
    async with ingest_run(conn, "statcan_csi") as r:
        r.rows_written = await load_csi_and_offence_map(conn)
        r.data_as_of = datetime(2009, 12, 31, tzinfo=UTC)  # edition year of the published table
    async with ingest_run(conn, "tps_ncr") as r:
        r.rows_written = await load_neighbourhoods(conn, client, region_id)
        r.rows_written += await build_cells(conn, region_id)
        r.data_as_of = datetime(NCR_YEAR, 12, 31, tzinfo=UTC)
