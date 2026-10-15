"""Patterns in police reports (01-03-news.md, criterion 40)."""

from datetime import date, timedelta

import pytest

from uavert.scoring import patterns

NEWEST = date(2026, 10, 1)


def series(area, offence, recent, per_month_before):
    """`recent` incidents in the latest 30 days, and `per_month_before` in each of the 12 months before."""
    out = [(area, offence, NEWEST - timedelta(days=i % 30)) for i in range(recent)]
    for m in range(12):
        out += [(area, offence, NEWEST - timedelta(days=35 + 30 * m)) for _ in range(per_month_before)]
    return out


def test_chance_of_at_least():
    assert patterns.chance_of_at_least(0, 3.0) == 1.0
    assert patterns.chance_of_at_least(1, 2.0) == pytest.approx(1 - 2.718281828 ** -2)


def test_a_clear_spike_is_a_pattern():
    # Broadview North's real figures: 7 break-ins against about 1.2 a month
    found = patterns.find(series("Broadview North", "break_and_enter", 7, 1), NEWEST)
    assert len(found) == 1
    p = found[0]
    assert (p.area, p.recent, p.first_date, p.last_date) == ("Broadview North", 7, date(2026, 9, 2), NEWEST)
    assert p.usual_per_30_days == pytest.approx(12 * 30 / 365) and p.chance < 0.01 and p.times_usual > 5


def test_too_few_is_not_a_pattern():
    assert patterns.find(series("Quiet", "break_and_enter", 4, 0), NEWEST) == []


def test_high_but_could_be_chance_is_not_a_pattern():
    # 9 against a usual 4 a month: more than twice usual, but about a 2% chance
    assert patterns.find(series("Busy", "motor_vehicle_theft", 9, 4), NEWEST) == []
    assert patterns.chance_of_at_least(9, 4 * 365 / 12 * 12 / 365) > 0.01


def test_only_break_ins_and_auto_thefts():
    assert patterns.find(series("Anywhere", "assault_1", 30, 1), NEWEST) == []
