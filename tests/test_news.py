from datetime import UTC, datetime, timedelta
from pathlib import Path

import h3
import pytest

from uavert import db
from uavert.ingest import news as news_ingest
from uavert.ingest.runs import ensure_reference_rows
from uavert.scoring.combine import combine
from uavert.scoring.news import NewsSignal, news_score
from uavert.sources import news
from uavert.sources.geocode import Place

FIX = Path(__file__).parent / "fixtures" / "news"
NOW = datetime(2026, 10, 1, 18, tzinfo=UTC)
HOODS = ["Kensington-Chinatown", "Moss Park", "Annex", "Glenfield-Jane Heights"]


def test_parse_real_cbc_feed():
    items = news.parse_cbc_rss((FIX / "cbc_toronto.xml").read_text(encoding="utf-8"))
    assert len(items) == 20
    assert items[0].publisher == "CBC News" and items[0].url.startswith("https://www.cbc.ca/")
    assert all(i.published_at.tzinfo for i in items)


def test_none_of_todays_real_cbc_stories_is_flagged():
    """The 20 CBC Toronto stories of 2026-10-01: elections, housing, wage, collisions outside Toronto,
    Peel thefts, sport. Including "Torontonians don't feel safe..." which must not be flagged."""
    items = news.parse_cbc_rss((FIX / "cbc_toronto.xml").read_text(encoding="utf-8"))
    flagged = [(i.headline, news.classify(i.headline, i.summary)) for i in items if news.classify(i.headline, i.summary)]
    assert flagged == []


# Made-up examples in the style of local headlines (not real reports), to check labels and places.
@pytest.mark.parametrize("headline,summary,label,place", [
    ("Man injured in shooting near Jane and Finch", "Toronto police say a man was taken to hospital.", "violent_incident", "Jane and Finch"),
    ("Woman stabbed at Queen Street West and Spadina Avenue", "", "violent_incident", "Queen Street West and Spadina Avenue"),
    ("Police investigating robbery in Kensington-Chinatown", "", "violent_incident", "Kensington-Chinatown"),
    ("Hundreds join protest at Queen's Park", "Demonstrators gathered on Saturday.", "protest", None),
    ("Protesters block traffic near Bloor and Spadina area", "", "protest", "Bloor and Spadina"),
    ("Man charged after carjacking in Moss Park", "", "violent_incident", "Moss Park"),
    ("Mayoral candidates debate safety after shooting", "", None, None),
    ("Accused sentenced in 2019 homicide", "", None, None),
    ("Leafs' late shot sinks Canadiens", "", None, None),
    ("Mississauga shooting leaves one injured", "Peel police are investigating.", None, None),
    ("Flu shot clinics open across Toronto", "", None, None),
    ("New bike lanes open on Bloor Street", "", None, None),
])
def test_classify_and_extract_place(headline, summary, label, place):
    assert news.classify(headline, summary) == label
    if label:
        assert news.extract_place(f"{headline}. {summary}", HOODS) == place


# ---- Types of event (01-03-news.md, criterion 36): real headlines from 2026-10-04 to 2026-10-15 ----
@pytest.mark.parametrize("headline,label", [
    ("Second Harvest theft: Arrest made as Toronto police seek second suspect", "property_crime"),
    ("Police arrest man in connection with Second Harvest thefts over Thanksgiving weekend", "property_crime"),
    ("Where North York home break-ins were reported this week", "property_crime"),
    ("Man facing arson charge week after hundreds of Israeli flags torched at North York church: police", "property_crime"),
    ("Two people arrested as protest disrupts Bloor Street bike lane removal in Etobicoke", "protest"),
    ("Cyclists continue protest as bike lane removal work underway in Etobicoke", "protest"),
    ("Police investigate man's death in North York as homicide", "violent_incident"),
    ("Seven charged in Toronto kidnapping investigation, ammo stolen from Canadian military, police say", "violent_incident"),
    # sport, and an event from an earlier year: not current incidents
    ("Toronto Sixers rally past Vancouver Warriors to repeat as Canada Super60 women's cricket champions", None),
    ("Memorial held for Toronto boy shot and killed by stray bullet in 2025", None),
])
def test_types_of_event_from_real_headlines(headline, label):
    assert news.classify(headline, "", year=2026) == label


def test_an_earlier_year_only_counts_against_the_story_year():
    assert news.classify("Man shot near Jane and Finch in 2025", "", year=2025) == "violent_incident"


def test_property_words_never_outrank_violence():
    assert news.classify("Man stabbed during break-in at Annex home", "") == "violent_incident"


def test_property_crime_news_is_listed_but_never_scored():
    # Criterion 41: a fresh property-crime story right on the cell changes nothing
    cell = h3.latlng_to_cell(43.6536, -79.3840, 9)
    assert news_score([signal(1, "property_crime", cell)], NOW, cell=cell) == (0, [])
    assert news_score([signal(1, "property_crime", cell)], NOW, neighbourhood_id=76) == (0, [])


def signal(hours_ago, category="violent_incident", cell=None):
    return NewsSignal("Man injured in shooting", "https://example.test/a", "CBC News", category,
                      NOW - timedelta(hours=hours_ago), cell or h3.latlng_to_cell(43.6536, -79.3840, 9), 76)


# Criterion 16: located reports raise nearby cells, are labelled unverified, expire, never pass "elevated".
def test_news_raises_nearby_cells_and_fades_over_24_hours():
    here = h3.latlng_to_cell(43.6536, -79.3840, 9)
    two_rings_away = next(iter(h3.grid_ring(here, 2)))
    far = h3.latlng_to_cell(43.75, -79.30, 9)
    assert news_score([signal(0)], NOW, cell=here)[0] == 74
    assert news_score([signal(12)], NOW, cell=here)[0] == 37
    assert news_score([signal(24)], NOW, cell=here) == (0, [])
    assert news_score([signal(0)], NOW, cell=two_rings_away)[0] == 74
    assert news_score([signal(0)], NOW, cell=far) == (0, [])
    assert news_score([signal(0, "protest")], NOW, cell=here)[0] == 60


def test_news_reason_is_labelled_unverified_with_link():
    _, reasons = news_score([signal(2)], NOW, cell=h3.latlng_to_cell(43.6536, -79.3840, 9))
    assert reasons[0].text == "Unverified news report: Man injured in shooting (CBC News, 2 h ago)"
    assert reasons[0].url == "https://example.test/a" and reasons[0].as_of


def test_news_alone_never_reaches_high():
    here = h3.latlng_to_cell(43.6536, -79.3840, 9)
    score, reasons = news_score([signal(0), signal(0.1), signal(1)], NOW, cell=here)
    combined = combine({"crime": 20, "news": score}, reasons)
    assert combined.score == 74 and combined.band == "elevated"


def test_neighbourhood_news_counts_reports_inside_it():
    assert news_score([signal(0)], NOW, neighbourhood_id=76)[0] == 74
    assert news_score([signal(0)], NOW, neighbourhood_id=5) == (0, [])


class FakeGeocoder:
    async def search(self, query):
        return {"jane and finch, toronto, ontario": Place("Jane and Finch", -79.5196, 43.7621),
                "bloor and spadina, toronto, ontario": Place("Bloor and Spadina", -79.4036, 43.6672)}.get(query.lower())


@pytest.mark.db
async def test_store_locates_toronto_stories_and_skips_unlabelled(test_db_url):
    conn = await db.connect(test_db_url)
    try:
        region_id = await ensure_reference_rows(conn)
        await conn.execute("DELETE FROM news_events WHERE url LIKE 'https://example.test/%'")
        await conn.execute(
            "INSERT INTO neighbourhoods (region_id, external_id, name, valid_year, geom) VALUES"
            " ($1, 'JF', 'Test Jane', 2025, ST_GeomFromText('MULTIPOLYGON(((-79.53 43.75,-79.51 43.75,-79.51 43.77,-79.53 43.77,-79.53 43.75)))', 4326))"
            " ON CONFLICT DO NOTHING", region_id)
        items = [
            news.NewsItem("news_cbc", "CBC News", "Man injured in shooting near Jane and Finch", "", "https://example.test/1", NOW - timedelta(hours=1)),
            news.NewsItem("news_cbc", "CBC News", "Protest planned downtown", "", "https://example.test/2", NOW - timedelta(hours=1)),
            news.NewsItem("news_cbc", "CBC News", "Protesters gather near Bloor and Spadina", "", "https://example.test/3", NOW - timedelta(hours=1)),
            news.NewsItem("news_cbc", "CBC News", "Board of trade urges reform", "", "https://example.test/4", NOW - timedelta(hours=1)),
            # windows by type (01-03-news.md): violent 7 days, protest 2 days, property crime 60 days
            news.NewsItem("news_cbc", "CBC News", "Shooting near Jane and Finch", "", "https://example.test/5", NOW - timedelta(days=8)),
            news.NewsItem("news_star", "Toronto Star", "Protest planned downtown again", "", "https://example.test/6", NOW - timedelta(days=3)),
            news.NewsItem("news_star", "Toronto Star", "Where Etobicoke home break-ins were reported this week", "",
                          "https://example.test/7", NOW - timedelta(days=50)),
        ]
        stored = await news_ingest.store(conn, region_id, items, FakeGeocoder(), now=NOW)
        rows = {r["url"]: r for r in await conn.fetch(
            "SELECT url, category, location_text, h3::text AS h3, collected_at FROM news_events WHERE url LIKE 'https://example.test/%'")}
        # 3 is outside every test neighbourhood, 4 isn't labelled, 5 and 6 are past their type's window
        assert stored == 3 and set(rows) == {"https://example.test/1", "https://example.test/2", "https://example.test/7"}
        assert rows["https://example.test/7"]["category"] == "property_crime"
        assert rows["https://example.test/1"]["h3"] and rows["https://example.test/1"]["location_text"] == "Jane and Finch"
        assert rows["https://example.test/2"]["h3"] is None  # citywide: listed, changes no score
        assert all(r["collected_at"] for r in rows.values())
    finally:
        await conn.execute("DELETE FROM news_events WHERE url LIKE 'https://example.test/%'")
        await conn.execute("DELETE FROM neighbourhoods WHERE external_id = 'JF'")
        await conn.close()
