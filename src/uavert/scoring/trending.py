"""Trending news (01-03-news.md): stories about the same event, grouped by the significant words their headlines share.
Information only; nothing here changes a score."""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

LINK_WORDS = 3  # stories sharing at least this many significant words are about the same event (2 joined unrelated
                # stories that only shared a place, "North York")...
LINK_DAYS = 3  # ...when published within this many days of each other
MIN_STORIES = 3  # a group is trending with this many stories in the last TRENDING_DAYS...
MIN_OUTLETS = 2  # ...from at least this many outlets
TRENDING_DAYS = 3

# Words that say nothing about which event a story is about.
STOP = frozenset("""
a an and are as at be been by for from has have he her his in into is it its of on or over she that the their they this
to was were what when where which who will with after amid about against before during new more says say said than
toronto torontonians gta ontario canada canadian police tps man woman men women people person year years old week weeks
day days today yesterday arrest arrested arrests charge charged charges suspect suspects accused report reports
""".split())


@dataclass(frozen=True)
class Story:
    headline: str
    url: str
    publisher: str
    category: str
    published_at: datetime


def words(headline: str) -> frozenset[str]:
    """Significant words: lower case, possessives and simple plurals removed, common words dropped."""
    out = set()
    for w in re.findall(r"[a-z0-9][a-z0-9'-]*", headline.lower()):
        w = re.sub(r"'s$", "", w).strip("'-")
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        if len(w) > 2 and w not in STOP and not w.isdigit():
            out.add(w)
    return frozenset(out)


def groups(stories: list[Story]) -> list[list[Story]]:
    """Stories joined when they share LINK_WORDS significant words within LINK_DAYS (joined transitively)."""
    parent = list(range(len(stories)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    ws = [words(s.headline) for s in stories]
    for i in range(len(stories)):
        for j in range(i + 1, len(stories)):
            close = abs(stories[i].published_at - stories[j].published_at) <= timedelta(days=LINK_DAYS)
            if close and len(ws[i] & ws[j]) >= LINK_WORDS:
                parent[root(i)] = root(j)
    out: dict[int, list[Story]] = {}
    for i, s in enumerate(stories):
        out.setdefault(root(i), []).append(s)
    return [sorted(g, key=lambda s: s.published_at, reverse=True) for g in out.values()]


def trending(stories: list[Story], now: datetime) -> list[dict]:
    """Groups with MIN_STORIES stories from MIN_OUTLETS outlets in the last TRENDING_DAYS, most stories first."""
    out = []
    for g in groups(stories):
        recent = [s for s in g if now - s.published_at <= timedelta(days=TRENDING_DAYS)]
        outlets = {s.publisher for s in recent}
        if len(recent) < MIN_STORIES or len(outlets) < MIN_OUTLETS:
            continue
        newest = g[0]
        out.append({
            "headline": newest.headline, "url": newest.url, "publisher": newest.publisher,
            "published_at": newest.published_at.isoformat(),
            "category": Counter(s.category for s in g).most_common(1)[0][0],
            "story_count": len(g), "outlet_count": len({s.publisher for s in g}),
            "first_published_at": g[-1].published_at.isoformat(),
            "stories": [{"headline": s.headline, "url": s.url, "publisher": s.publisher,
                         "published_at": s.published_at.isoformat()} for s in g],
        })
    out.sort(key=lambda t: t["published_at"], reverse=True)  # newest first among groups of the same size
    return sorted(out, key=lambda t: -t["story_count"])
