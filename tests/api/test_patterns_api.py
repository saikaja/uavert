"""Patterns in police reports (01-03-news.md, criteria 40 and 41)."""

import pytest

pytestmark = pytest.mark.db


@pytest.fixture
async def pattern(test_pool, seeded):
    await test_pool.execute(
        "INSERT INTO crime_patterns (neighbourhood_id, offence, recent, usual_per_30_days, chance, first_date, last_date,"
        " source_key) VALUES ($1, 'break_and_enter', 7, 1.2, 0.0002, '2026-09-01', '2026-09-30', 'tps_mci')", seeded["T2"])
    yield
    await test_pool.execute("DELETE FROM crime_patterns")


async def test_crime_patterns_lists_counts_usual_and_dates(client, pattern):
    data = (await client.get("/api/v1/crime-patterns")).json()["data"]
    assert data == [{
        "neighbourhood_id": data[0]["neighbourhood_id"], "neighbourhood": "Test East", "offence": "break_and_enter",
        "offence_label": "break-ins", "recent": 7, "usual_per_30_days": 1.2, "times_usual": 5.8,
        "first_date": "2026-09-01", "last_date": "2026-09-30", "data_as_of": "2026-09-30", "source_key": "tps_mci",
        "computed_at": data[0]["computed_at"]}]


async def test_neighbourhood_shows_its_own_pattern_and_its_score_is_unchanged(client, seeded, pattern):
    east = (await client.get(f"/api/v1/neighbourhoods/{seeded['T2']}")).json()["data"]
    assert [p["recent"] for p in east["patterns"]] == [7]
    assert east["categories"]["crime"] == 20  # the seeded score: a pattern never changes it
    centre = (await client.get(f"/api/v1/neighbourhoods/{seeded['T1']}")).json()["data"]
    assert centre["patterns"] == []
