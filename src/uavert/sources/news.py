"""News signals: CBC Toronto RSS (main) and GDELT (extra). Keyword classification and place extraction.

Only the headline, link, publisher and time are kept. Classification is deliberately cautious:
stories about elections, courts, sport or other regions are skipped.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from uavert.config import get_settings
from uavert.sources.http import SourceUnavailable, get, get_json


@dataclass(frozen=True)
class NewsItem:
    source_key: str
    publisher: str
    headline: str
    summary: str
    url: str
    published_at: datetime


def _words(*terms: str) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(terms) + r")\b", re.I)


VIOLENT = _words(r"shootings?", r"shot", r"shots fired", r"gunfire", r"gunshots?", r"stabbings?", r"stabbed",
                 r"homicides?", r"murder(?:ed)?", r"assault(?:ed)?", r"robbery", r"robbed", r"carjack(?:ing|ed)",
                 r"swarming", r"armed (?:man|suspect)", r"kidnapp(?:ing|ed)")
PROTEST = _words(r"protests?", r"protesters?", r"protestors?", r"demonstrations?", r"demonstrators?", r"rally",
                 r"rallies", r"marchers", r"marched", r"blockades?", r"encampment clearing")
# Property crime (01-03-news.md): shown for 60 days, never scored.
PROPERTY = _words(r"break-ins?", r"break and enters?", r"burglar(?:y|ies|s)?", r"thefts?", r"thie(?:f|ves)", r"stolen",
                  r"catalytic converters?", r"arson", r"vandali[sz](?:m|ed)", r"shoplift(?:ing|ers?)")
NEGATIVE = _words(r"feel safe", r"mayoral", r"election", r"candidates?", r"debates?", r"trial", r"sentenc(?:ed|ing)",
                  r"verdict", r"anniversary", r"inquest", r"years ago", r"years after", r"cold case", r"documentary",
                  r"NHL", r"NBA", r"MLB", r"Leafs", r"Blue Jays", r"Jays", r"Raptors", r"Argonauts", r"TFC", r"goal",
                  r"season", r"playoffs?", r"overtime",
                  r"flu shot", r"vaccine", r"rall(?:y|ies|ied) past", r"champions?(?:hip)?", r"cricket", r"tournament",
                  r"memorial")
EARLIER_YEAR = re.compile(r"\b(?:in|since|from) ((?:19|20)\d\d)\b")
OTHER_REGIONS = _words(r"Mississauga", r"Brampton", r"Peel", r"York Region", r"York police", r"Durham", r"Vaughan",
                       r"Markham", r"Richmond Hill", r"Ajax", r"Pickering", r"Oshawa", r"Hamilton", r"Halton",
                       r"Oakville", r"Burlington", r"OPP", r"Ontario Provincial Police")

INTERSECTION = re.compile(
    r"\b(?:near|at|in the|around|close to)\s+((?:[A-Z][\w'-]*\s){0,3}[A-Z][\w'-]*)\s+and\s+((?:[A-Z][\w'-]*\s){0,3}[A-Z][\w'-]*)")


def classify(headline: str, summary: str = "", year: int | None = None) -> str | None:
    """'violent_incident', 'protest', 'property_crime' or None. Headline and summary are both read.
    `year` (the story's year, default this year): a story about an event "in" an earlier year is skipped."""
    text = f"{headline}. {summary}"
    if NEGATIVE.search(text) or OTHER_REGIONS.search(text):
        return None
    year = year or datetime.now(UTC).year
    if any(int(y) < year for y in EARLIER_YEAR.findall(text)):
        return None
    if VIOLENT.search(text):
        return "violent_incident"
    if PROTEST.search(text):
        return "protest"
    if PROPERTY.search(text):
        return "property_crime"
    return None


def extract_place(text: str, neighbourhood_names: list[str]) -> str | None:
    """An intersection ("Jane and Finch") or a Toronto neighbourhood name mentioned in the text."""
    m = INTERSECTION.search(text)
    if m:
        a, b = m.group(1).strip(), re.sub(r"\s+(?:area|streets|avenues|intersection)$", "", m.group(2).strip())
        return f"{a} and {b}"
    for name in sorted(neighbourhood_names, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", text):
            return name
    return None


# RSS feeds read alike (01-03-news.md): source key -> (publisher, config field with the feed's address).
RSS_FEEDS = {
    "news_cbc": ("CBC News", "cbc_rss_url"),
    "news_citynews": ("CityNews", "citynews_rss_url"),
    "news_global": ("Global News", "global_rss_url"),
    "news_star": ("Toronto Star", "star_rss_url"),
}


def parse_cbc_rss(xml_text: str) -> list[NewsItem]:
    return parse_rss(xml_text, "news_cbc")


def parse_rss(xml_text: str, source_key: str) -> list[NewsItem]:
    """Standard RSS 2.0 items: title, link, publication date and description (tags removed)."""
    publisher = RSS_FEEDS[source_key][0]
    root = ET.fromstring(xml_text)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        if not (title and link and pub):
            continue
        summary = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        items.append(NewsItem(source_key, publisher, title, " ".join(summary.split()), link,
                              parsedate_to_datetime(pub).astimezone(UTC)))
    return items


def parse_gdelt(data: dict) -> list[NewsItem]:
    out = []
    for a in data.get("articles", []):
        if a.get("language") != "English" or "toronto" not in a.get("title", "").lower():
            continue
        published = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        out.append(NewsItem("news_gdelt", a.get("domain", "GDELT"), " ".join(a["title"].split()), "", a["url"], published))
    return out


async def fetch_rss(client: httpx.AsyncClient, source_key: str) -> list[NewsItem]:
    publisher, url_field = RSS_FEEDS[source_key]
    r = await get(client, getattr(get_settings(), url_field))
    try:
        return parse_rss(r.text, source_key)
    except ET.ParseError as e:
        raise SourceUnavailable(f"{publisher} RSS could not be read: {e}") from e


async def fetch_cbc(client: httpx.AsyncClient) -> list[NewsItem]:
    return await fetch_rss(client, "news_cbc")


async def fetch_gdelt(client: httpx.AsyncClient) -> list[NewsItem]:
    data = await get_json(client, get_settings().gdelt_url, {
        "query": "(shooting OR stabbing OR protest OR demonstration) toronto sourcecountry:canada sourcelang:english",
        "mode": "artlist", "format": "json", "maxrecords": 50, "timespan": "24h",
    })
    return parse_gdelt(data)
