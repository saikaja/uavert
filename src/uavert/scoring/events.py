"""Counting each crime event once across the Toronto Police datasets."""

from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


def count_once(records: Iterable[T], event_id: Callable[[T], str], weight: Callable[[T], float]) -> list[T]:
    """Keep one record per event: the one with the highest CSI weight.

    The same event can appear in several datasets (a fatal shooting is in Homicides, Shootings
    and Major Crime Indicators) and as several offences in one dataset. Keeping the most serious
    record means homicide beats shooting beats any other offence.
    """
    best: dict[str, T] = {}
    for r in records:
        key = event_id(r)
        if key not in best or weight(r) > weight(best[key]):
            best[key] = r
    return list(best.values())
