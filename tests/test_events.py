from uavert.scoring.events import count_once

W = {"murder": 7042, "discharge_firearm_intent": 988, "assault_2": 77, "robbery": 583}


def test_each_event_counted_once_with_its_most_serious_record():
    records = [
        ("GO-1", "tps_mci", "discharge_firearm_intent"),
        ("GO-1", "tps_shootings", "discharge_firearm_intent"),
        ("GO-1", "tps_homicides", "murder"),
        ("GO-2", "tps_mci", "assault_2"),
        ("GO-2", "tps_mci", "robbery"),
        ("GO-3", "tps_shootings", "discharge_firearm_intent"),
    ]
    kept = count_once(records, event_id=lambda r: r[0], weight=lambda r: W[r[2]])
    assert sorted(kept) == [
        ("GO-1", "tps_homicides", "murder"),
        ("GO-2", "tps_mci", "robbery"),
        ("GO-3", "tps_shootings", "discharge_firearm_intent"),
    ]
