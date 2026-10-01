from fastapi import APIRouter, Request

from uavert.api import live
from uavert.config import get_settings
from uavert.freshness import iso
from uavert.scoring import alerts, crime, environment, fairness
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
         "as_of": iso(r["data_as_of"]), "collected_at": iso(r["last_collected_at"]),
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
    check = await pool.fetchrow(
        "SELECT computed_at, rho_income, rho_low_income, n, label, census_year FROM fairness_checks ORDER BY id DESC LIMIT 1")
    bands = [{"band": b, "label": BAND_LABELS[b], "min_score": lo,
              "max_score": (BANDS[i + 1][1] - 1) if i + 1 < len(BANDS) else 100} for i, (b, lo) in enumerate(BANDS)]
    return live.envelope({
        "bands": bands,
        "combination": "highest category score (crime, environment, alert, news), never an average",
        "csi_edition": edition,
        "csi_weights": [dict(w) | {"weight": float(w["weight"]), "retrieved_on": w["retrieved_on"].isoformat()} for w in weights],
        "offence_map": [dict(m) | {"weight": float(m["weight"])} for m in mapping],
        "fairness": None if check is None else {
            "computed_at": check["computed_at"].isoformat(), "neighbourhoods": check["n"], "census_year": check["census_year"],
            "rho_median_household_income": round(check["rho_income"], 2) if check["rho_income"] is not None else None,
            "rho_low_income_share": round(check["rho_low_income"], 2) if check["rho_low_income"] is not None else None,
            "label": check["label"], "review_threshold": fairness.REVIEW_THRESHOLD,
            "method": "Spearman rank correlation between neighbourhood crime scores and 2021 Census income",
        },
        "activity_by_hour": [{"hour": h, "factor": round(factor, 3), "basis": basis}
                             for h, (factor, basis) in enumerate(ctx.activity)],
        "parameters": {
            "neighbourhood_year": 2025,
            "street_window_days": 365,
            "half_life_days": crime.HALF_LIFE_DAYS,
            "neighbour_ring_weight": crime.RING_WEIGHT,
            "min_incidents_for_own_score": crime.MIN_INCIDENTS,
            "street_premises": sorted(crime.STREET_PREMISES),
            "aqhi_breakpoints": environment.BREAKPOINTS,
            "aqhi_stale_after_hours": environment.STALE_AFTER.total_seconds() / 3600,
            "foot_traffic_floor_per_hour": crime.FOOT_TRAFFIC_FLOOR,
            "foot_traffic_since": crime.FOOT_TRAFFIC_SINCE.isoformat(),
            "foot_traffic_max_rings": crime.FOOT_TRAFFIC_MAX_RINGS,
            "busy_area_quantile": crime.BUSY_AREA_QUANTILE,
            "surroundings_rings": crime.SURROUNDINGS_RINGS,
            "standout_min_ratio": crime.STANDOUT_MIN_RATIO,
            "time_window_hours": crime.TIME_WINDOW,
            "time_prior_weight": crime.TIME_PRIOR_WEIGHT,
            "warning_score": alerts.TOP_BAND_SCORE,
            "advisory_score": alerts.ADVISORY_SCORE,
        },
    }, ctx)
