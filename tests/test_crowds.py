"""Criteria 49-51: large City events on their dates, and major venues as context."""

from datetime import UTC, date, datetime

from uavert.ingest.crowds import match_large_events
from uavert.ingest.reference import DATA_DIR, read_csv
from uavert.scoring.crowds import EVENT_SCORE, CrowdEvent, Venue, crowds_score

PATTERNS = read_csv(DATA_DIR / "large_city_events.csv")
SAT, FRI, SUN = date(2026, 10, 3), date(2026, 10, 2), date(2026, 10, 4)


def ms(d: date, hour=23):  # Toronto evening -> epoch ms (EDT is UTC-4)
    return int(datetime(d.year, d.month, d.day, hour - 4 if hour >= 4 else hour, tzinfo=UTC).timestamp() * 1000)


def entry(id_, name, days, location="", featured="No"):
    return {"id": id_, "event_name": name, "featured_event": featured,
            "event_dates": [{"date": ms(d), "locations": [f"Venue: {location}"] if location else []} for d in days]}


def test_main_event_with_various_location_uses_the_default():
    found = match_large_events([entry("1", "Nuit Blanche 2026", [SAT], "Various", featured="Yes")], PATTERNS, FRI, SUN)
    assert len(found) == 1 and found[0].location is None and found[0].default_location == "Nathan Phillips Square, Toronto"


def test_spin_offs_count_only_on_the_main_event_dates_and_duplicates_collapse():
    raw = [
        entry("1", "Nuit Blanche 2026", [SAT], "Various", featured="Yes"),
        entry("2", "Nuit Blanche at 401 Richmond", [SAT], "401 Richmond St W, Toronto"),
        entry("3", "Nuit Blanche Artist Meet and Greet", [FRI], "22 Elm St, Toronto"),  # day before: not a crowd
        entry("4", "Nuit Blanche at 401 Richmond", [SAT], "401 Richmond St W, Toronto"),  # listed twice
        entry("5", "Library book club", [SAT], "1 Main St"),  # no pattern
    ]
    found = sorted((f.name, f.event_date) for f in match_large_events(raw, PATTERNS, FRI, SUN))
    assert found == [("Nuit Blanche 2026", SAT), ("Nuit Blanche at 401 Richmond", SAT)]


def test_without_a_featured_entry_all_matches_count():
    found = match_large_events([entry("9", "Santa Claus Parade", [SAT], "Queen's Park, Toronto")], PATTERNS, FRI, SUN)
    assert [f.pattern_key for f in found] == ["santa_parade"]


CITY_HALL = (-79.3838, 43.6527)
NUIT = CrowdEvent("Nuit Blanche 2026", SAT, *CITY_HALL)
ROGERS = Venue("Rogers Centre", 39150, -79.3889, 43.6414)


def test_event_raises_crowds_to_moderate_on_its_date_only():
    score, reasons = crowds_score(-79.3810, 43.6540, SAT, [NUIT], [], today=SAT)
    assert score == EVENT_SCORE == 35
    assert reasons[0].text.startswith("Nuit Blanche 2026 today, about") and "large crowds and road closures" in reasons[0].text
    assert crowds_score(-79.3810, 43.6540, SUN, [NUIT], [], today=SAT) == (0, [])
    # chosen for another day: says which day
    _, reasons = crowds_score(-79.3810, 43.6540, SAT, [NUIT], [], today=FRI)
    assert "on Sat Oct 3" in reasons[0].text


def test_far_from_the_event_no_effect():
    assert crowds_score(-79.50, 43.75, SAT, [NUIT], [], today=SAT) == (0, [])


def test_venue_is_context_only():
    score, reasons = crowds_score(-79.3880, 43.6420, SAT, [], [ROGERS], today=SAT)  # 125 Blue Jays Way area
    assert score == 0
    assert reasons[0].text == "Near Rogers Centre: can draw about 39,150 people on event days"


def test_venue_list_has_sources():
    rows = read_csv(DATA_DIR / "major_venues.csv")
    assert rows and all(int(r["capacity"]) >= 5000 and r["source_url"].startswith("https://") for r in rows)
