from fastapi import APIRouter, Request

from uavert.api import live
from uavert.config import get_settings
from uavert.scoring import alerts, crime, environment
from uavert.scoring.bands import BAND_LABELS, BANDS

router = APIRouter(tags=["data sources"])


@router.get("/sources", summary="Every data source: licence, attribution, data date and collection time")
async def list_sources(request: Request):
    pool = request.app.state.pool
    rows = await pool.fetch(
        "SELECT key, name, url, licence, attribution, data_as_of, last_collected_at, last_status, last_error"
        " FROM sources ORDER BY key"
    )
    ctx = await live.load(pool)
    return live.envelope([
        {"key": r["key"], "name": r["name"], "url": r["url"], "licence": r["licence"], "attribution": r["attribution"],
         "as_of": _iso(r["data_as_of"]), "collected_at": _iso(r["last_collected_at"]),
         "last_status": r["last_status"], "last_error": r["last_error"]}
        for r in rows
    ], ctx)


@router.get("/scoring-rules", summary="How scores are calculated: bands, CSI weights, offence map, parameters")
async def scoring_rules(request: Request):
    pool = request.app.state.pool
    edition = get_settings().csi_edition
    weights = await pool.fetch(
        "SELECT offence_key, label, weight, source_url, retrieved_on FROM csi_weights WHERE edition = $1 ORDER BY weight DESC",
        edition,
    )
    mapping = await pool.fetch(
        "SELECT m.source_key, m.ucr_code, m.ucr_ext, m.offence_label, m.csi_offence_key, w.label AS csi_label, m.match, m.group_label, w.weight"
        " FROM offence_map m JOIN csi_weights w ON w.edition = $1 AND w.offence_key = m.csi_offence_key"
        " ORDER BY w.weight DESC, m.offence_label",
        edition,
    )
    ctx = await live.load(pool)
    bands = [{"band": b, "label": BAND_LABELS[b], "min_score": lo,
              "max_score": (BANDS[i + 1][1] - 1) if i + 1 < len(BANDS) else 100} for i, (b, lo) in enumerate(BANDS)]
    return live.envelope({
        "bands": bands,
        "combination": "highest category score (crime, environment, alert, news), never an average",
        "csi_edition": edition,
        "csi_weights": [dict(w) | {"weight": float(w["weight"]), "retrieved_on": w["retrieved_on"].isoformat()} for w in weights],
        "offence_map": [dict(m) | {"weight": float(m["weight"])} for m in mapping],
        "parameters": {
            "neighbourhood_year": 2025,
            "street_window_days": 365,
            "half_life_days": crime.HALF_LIFE_DAYS,
            "neighbour_ring_weight": crime.RING_WEIGHT,
            "min_incidents_for_own_score": crime.MIN_INCIDENTS,
            "street_premises": sorted(crime.STREET_PREMISES),
            "aqhi_breakpoints": environment.BREAKPOINTS,
            "aqhi_stale_after_hours": environment.STALE_AFTER.total_seconds() / 3600,
            "warning_score": alerts.TOP_BAND_SCORE,
            "advisory_score": alerts.ADVISORY_SCORE,
        },
    }, ctx)


def _iso(t):
    return t.isoformat() if t else None
