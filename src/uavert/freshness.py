"""Data dates and collection times, in the one shape every score and response uses."""

from datetime import datetime


def iso(t: datetime | None) -> str | None:
    return t.isoformat() if t else None


async def source_dates(db, keys: list[str] | None = None) -> dict[str, dict]:
    """{source_key: {"as_of": data date, "collected_at": last successful collection}}. `db` is a
    connection or pool; `keys` limits the sources returned."""
    rows = await db.fetch(
        "SELECT key, data_as_of, last_collected_at FROM sources WHERE $1::text[] IS NULL OR key = ANY($1) ORDER BY key",
        keys,
    )
    return {r["key"]: {"as_of": iso(r["data_as_of"]), "collected_at": iso(r["last_collected_at"])} for r in rows}
