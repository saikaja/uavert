import pytest

from uavert.ingest.reference import DATA_DIR, UnmappedOffence, load_offence_map, read_csv


def test_csv_header_records_source_and_retrieval_date():
    head = (DATA_DIR / "csi_weights.csv").read_text(encoding="utf-8").splitlines()[:5]
    assert any("t001-eng.htm" in l for l in head)
    assert any("Retrieved: 2026-10-01" in l for l in head)


def test_csi_weights_match_published_values():
    w = {r["offence_key"]: float(r["weight"]) for r in read_csv(DATA_DIR / "csi_weights.csv")}
    assert w["murder"] == 7042 and w["robbery"] == 583 and w["break_and_enter"] == 187 and w["assault_1"] == 23


def test_every_mapping_points_at_a_published_weight():
    keys = {r["offence_key"] for r in read_csv(DATA_DIR / "csi_weights.csv")}
    assert {m.csi_offence_key for m in load_offence_map().rows()} <= keys


def test_exact_code_wins_over_wildcard():
    m = load_offence_map()
    assert m.resolve("tps_mci", "1450", "120").match == "exact"
    assert m.resolve("tps_mci", "1450", "100").match == "closest"
    assert m.resolve("tps_shootings", "*", "*").csi_offence_key == "discharge_firearm_intent"


def test_unmapped_offence_stops_with_its_name():
    m = load_offence_map()
    with pytest.raises(UnmappedOffence, match="1234-100 'Made Up Offence'"):
        m.check({("tps_mci", "1610", "100", "Robbery With Weapon"), ("tps_mci", "1234", "100", "Made Up Offence")})


def test_all_offences_seen_in_last_12_months_are_mapped():
    # (UCR code, ext) pairs returned by Toronto Police MCI for 2025-07-01 onwards, queried 2026-10-01.
    seen = ["1430-100", "2135-210", "2120-200", "1420-100", "2130-210", "1460-100", "1420-110", "2120-220",
            "1610-100", "1610-220", "2132-200", "1610-200", "2120-210", "1610-210", "1610-130", "1410-100",
            "2130-211", "1450-120", "1610-140", "1610-180", "1480-100", "1457-100", "1450-100", "1480-110",
            "2130-200", "1461-100", "2133-200", "1610-150", "1430-110", "1460-110", "2130-215", "1610-110",
            "1470-100", "1455-100", "2120-230", "1610-190", "1610-170", "1610-160", "2130-220", "1462-100",
            "1410-110", "1440-100", "2121-200"]
    load_offence_map().check({("tps_mci", *s.split("-"), "seen") for s in seen})
