"""Ingest steps by name, shared by the command line and the server's background refresh."""

import logging

import asyncpg

from uavert.ingest import crime, crowds, heat, live, news, reference, traffic
from uavert.ingest.runs import ensure_reference_rows
from uavert.sources.http import make_client

log = logging.getLogger("uavert.ingest")

STEPS = {
    "reference": reference.run, "cool_spaces": heat.run, "crowds": crowds.run, "crime": crime.run, "traffic": traffic.run, "aqhi": live.run_aqhi,
    "alerts": live.run_alerts, "news_gdelt": news.run_gdelt,
    **{key: news.rss_step(key) for key in ("news_cbc", "news_citynews", "news_global", "news_star")},
}
NEWS = ["news_cbc", "news_citynews", "news_global", "news_star", "news_gdelt"]
LIVE = ["aqhi", "alerts", *NEWS]
# Each target runs its steps in order; a failed step is reported and the rest still run.
TARGETS = {
    "reference": ["reference", "cool_spaces"],
    "heat": ["cool_spaces"],
    "crowds": ["crowds"],
    "crime": ["crime"],
    "traffic": ["traffic"],
    "aqhi": ["aqhi"],
    "alerts": ["alerts"],
    "news": NEWS,
    "live": LIVE,
    "daily": ["cool_spaces", "crowds", "crime", "traffic"],  # what the scheduled daily refresh reloads
    "all": ["reference", "cool_spaces", "crowds", "crime", "traffic", *LIVE],
}


async def run_steps(conn: asyncpg.Connection, names: list[str], report=print) -> list[str]:
    """Run the named steps in order. Returns the names that failed; each failure is already recorded
    in ingest_runs and the source's earlier data is kept."""
    failures = []
    region_id = await ensure_reference_rows(conn)
    async with make_client() as client:
        for name in names:
            report(f"Ingesting {name} ...")
            try:
                await STEPS[name](conn, client, region_id)
                report(f"  {name}: ok")
            except Exception as e:  # report and continue with the next source
                failures.append(name)
                report(f"  {name}: FAILED - {type(e).__name__}: {e}")
    return failures
