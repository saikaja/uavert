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
                 r"swarming", r"armed (?:man|suspect)")
PROTEST = _words(r"protests?", r"protesters?", r"protestors?", r"demonstrations?", r"demonstrators?", r"rally",
                 r"rallies", r"marchers", r"marched", r"blockades?", r"encampment clearing")
NEGATIVE = _words(r"feel safe", r"mayoral", r"election", r"candidates?", r"debates?", r"trial", r"sentenc(?:ed|ing)",
                  r"verdict", r"anniversary", r"inquest", r"years ago", r"years after", r"cold case", r"documentary",
                  r"NHL", r"NBA", r"MLB", r"Leafs", r"Blue Jays", r"Jays", r"Raptors", r"Argonauts", r"TFC", r"goal",
                  r"season", r"playoffs?", r"overtime",
                  r"flu shot", r"vaccine")
OTHER_REGIONS = _words(r"Mississauga", r"Brampton", r"Peel", r"York Region", r"York police", r"Durham", r"Vaughan",
                       r"Markham", r"Richmond Hill", r"Ajax", r"Pickering", r"Oshawa", r"Hamilton", r"Halton",
                       r"Oakville", r"Burlington", r"OPP", r"Ontario Provincial Police")

INTERSECTION = re.compile(
    r"\b(?:near|at|in the|around|close to)\s+((?:[A-Z][\w'-]*\s){0,3}[A-Z][\w'-]*)\s+and\s+((?:[A-Z][\w'-]*\s){0,3}[A-Z][\w'-]*)")


def classify(headline: str, summary: str = "") -> str | None:
    """'violent_incident', 'protest' or None. Headline and summary are both read."""
    text = f"{headline}. {summary}"
    if NEGATIVE.search(text) or OTHER_REGIONS.search(text):
        return None
    if VIOLENT.search(text):
        return "violent_incident"
    if PROTEST.search(text):
        return "protest"
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


def parse_cbc_rss(xml_text: str) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        if not (title and link and pub):
            continue
        summary = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        items.append(NewsItem("news_cbc", "CBC News", title, " ".join(summary.split()), link,
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


async def fetch_cbc(client: httpx.AsyncClient) -> list[NewsItem]:
    r = await get(client, get_settings().cbc_rss_url)
    try:
        return parse_cbc_rss(r.text)
    except ET.ParseError as e:
        raise SourceUnavailable(f"CBC RSS could not be read: {e}") from e


async def fetch_gdelt(client: httpx.AsyncClient) -> list[NewsItem]:
    data = await get_json(client, get_settings().gdelt_url, {
        "query": "(shooting OR stabbing OR protest OR demonstration) toronto sourcecountry:canada sourcelang:english",
        "mode": "artlist", "format": "json", "maxrecords": 50, "timespan": "24h",
    })
    return parse_gdelt(data)
