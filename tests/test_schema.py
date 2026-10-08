import pytest

pytestmark = pytest.mark.db

DATA_TABLES = [
    "regions", "sources", "neighbourhoods", "csi_weights", "offence_map", "incidents",
    "cells", "aqhi_readings", "official_alerts", "news_events", "neighbourhood_crime_years",
]


async def test_every_data_table_records_collection_time(test_pool):
    rows = await test_pool.fetch(
        "SELECT table_name FROM information_schema.columns"
        " WHERE table_schema = 'public' AND column_name = 'collected_at'"
    )
    assert set(DATA_TABLES) <= {r["table_name"] for r in rows}


async def test_computed_scores_record_compute_time(test_pool):
    rows = await test_pool.fetch(
        "SELECT table_name FROM information_schema.columns"
        " WHERE table_schema = 'public' AND column_name = 'computed_at'"
    )
    assert {"neighbourhood_scores", "cell_scores"} <= {r["table_name"] for r in rows}


async def test_incidents_unique_per_source_record(test_pool):
    keys = await test_pool.fetchval(
        "SELECT pg_get_indexdef(indexrelid) FROM pg_index"
        " WHERE indrelid = 'incidents'::regclass AND indisunique AND NOT indisprimary"
    )
    assert "source_key, event_id, ucr_code, ucr_ext" in keys
