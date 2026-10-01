"""Ingest steps by name, shared by the command line and the server's background refresh."""

import logging

import asyncpg

from uavert.ingest import crime, heat, live, news, reference, traffic
from uavert.ingest.runs import ensure_reference_rows
from uavert.sources.http import make_client

log = logging.getLogger("uavert.ingest")

STEPS = {
    "reference": reference.run, "cool_spaces": heat.run, "crime": crime.run, "traffic": traffic.run, "aqhi": live.run_aqhi,
    "alerts": live.run_alerts, "news_cbc": news.run_cbc, "news_gdelt": news.run_gdelt,
}
LIVE = ["aqhi", "alerts", "news_cbc", "news_gdelt"]
# Each target runs its steps in order; a failed step is reported and the rest still run.
TARGETS = {
    "reference": ["reference", "cool_spaces"],
    "heat": ["cool_spaces"],
    "crime": ["crime"],
    "traffic": ["traffic"],
    "aqhi": ["aqhi"],
    "alerts": ["alerts"],
    "news": ["news_cbc", "news_gdelt"],
    "live": LIVE,
    "all": ["reference", "cool_spaces", "crime", "traffic", *LIVE],
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
