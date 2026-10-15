"""Trending news (01-03-news.md, criterion 39), checked on the real labelled stories of 2026-10-09 to 2026-10-15."""

from datetime import UTC, datetime

from uavert.scoring.trending import Story, groups, trending, words

NOW = datetime(2026, 10, 15, 19, tzinfo=UTC)


def s(day, hour, publisher, category, headline):
    return Story(headline, f"https://example.test/{abs(hash(headline))}", publisher, category,
                 datetime(2026, 10, day, hour, tzinfo=UTC))


REAL = [
    s(15, 16, "CBC News", "property_crime", "29-year-old man arrested after Thanksgiving theft at Second Harvest charity: Toronto police"),
    s(15, 15, "CityNews", "property_crime", "Man, 29, arrested in catalytic convertor theft from Etobicoke food charity, 2 others in the area"),
    s(15, 14, "Toronto Star", "property_crime", "Police arrest man in connection with Second Harvest thefts over Thanksgiving weekend"),
    s(15, 13, "CityNews", "protest", "Cyclists continue protest as bike lane removal work underway in Etobicoke"),
    s(15, 12, "Toronto Star", "violent_incident", "Canadian military needs better ammo safeguards following kidnapping arrests, officials say"),
    s(15, 11, "Global News", "property_crime", "Second Harvest theft: Arrest made as Toronto police seek second suspect"),
    s(15, 10, "CBC News", "violent_incident", "Man arrested after 2 alleged sexual assaults at Scarborough school: Toronto police"),
    s(15, 9, "Toronto Star", "property_crime", "Second Harvest receives $60,000 donation to repair trucks damaged over Thanksgiving weekend"),
    s(14, 20, "Toronto Star", "protest", "Two people arrested as protest disrupts Bloor Street bike lane removal in Etobicoke"),
    s(14, 18, "CBC News", "property_crime", "Second Harvest receives $60K donation to repair 7 food trucks after catalytic converters stolen Sunday"),
    s(14, 17, "CBC News", "violent_incident", "3rd member of Canadian Armed Forces charged in kidnapping probe: Toronto police"),
    s(14, 16, "Toronto Star", "violent_incident", "Seven charged in Toronto kidnapping investigation, ammo stolen from Canadian military, police say"),
    s(14, 15, "CBC News", "protest", "Cyclists delay province's bike lane removal start in Toronto, 2 arrested"),
    s(14, 12, "Toronto Star", "protest", "Protesters block Ford government's removal of Bloor Street bike lanes in Etobicoke"),
    *[s(13, 12, "Toronto Star", "property_crime", f"Where {d} home break-ins were reported this week")
      for d in ("Etobicoke", "Scarborough", "East York", "North York", "York", "Old Toronto")],
    s(13, 15, "CBC News", "protest", "Man facing arson charge week after hundreds of Israeli flags torched at North York church: police"),
    s(9, 12, "CBC News", "violent_incident", "Toronto police officer who shot at man accused in Const. Marc Pinizzotto's death cleared of wrongdoing"),
]


def test_sharing_only_a_place_doesnt_join_stories():
    # Found in the browser check: with 2 shared words, "North York" joined this story to the Star's weekly round-ups
    arson = next(g for g in groups(REAL) if any("arson" in x.headline for x in g))
    assert len(arson) == 1


def find(result, text):
    return next(t for t in result if any(text in x["headline"] for x in t["stories"]))


def test_words_drop_common_words_and_plurals():
    assert words("Police arrest man in connection with Second Harvest thefts") == {"connection", "second", "harvest", "theft"}


def test_real_events_group_without_mixing():
    result = trending(REAL, NOW)
    harvest, bikes = find(result, "Second Harvest"), find(result, "bike lane")
    assert harvest is not bikes
    assert all("bike lane" not in x["headline"] for x in harvest["stories"])
    assert all("Harvest" not in x["headline"] for x in bikes["stories"])
    assert (bikes["story_count"], bikes["outlet_count"], bikes["category"]) == (4, 3, "protest")
    # CityNews's version ("catalytic convertor theft from Etobicoke food charity") shares only 2 words with the others
    assert (harvest["story_count"], harvest["outlet_count"], harvest["category"]) == (5, 3, "property_crime")
    assert result[0] is harvest  # most stories first
    assert harvest["headline"].startswith("29-year-old man arrested")  # the newest story leads


def test_one_outlets_series_is_not_trending():
    # the Star's six weekly round-ups group together, but come from one outlet
    weekly = next(g for g in groups(REAL) if "break-ins" in g[0].headline)
    assert len(weekly) == 6
    assert not any("break-ins" in x["headline"] for t in trending(REAL, NOW) for x in t["stories"])


def test_old_stories_dont_trend():
    assert trending(REAL, datetime(2026, 10, 25, tzinfo=UTC)) == []


def test_a_single_story_never_trends():
    assert trending(REAL[-1:], NOW) == []
