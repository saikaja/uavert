from uavert.ingest.reference import ExcludedPlace, load_excluded_places
from uavert.scoring.crime import at_excluded_place

JAIL = ExcludedPlace("Toronto South Detention Centre", "130 Horner Ave", -79.51581, 43.61208, 50, "Other", "jail")
METRE_LAT = 1 / 111_195  # degrees of latitude in one metre


def test_the_two_jails_are_listed_with_their_points():
    places = {p.name: p for p in load_excluded_places()}
    assert set(places) == {"Toronto South Detention Centre", "Toronto East Detention Centre"}
    assert (places["Toronto East Detention Centre"].lon, places["Toronto East Detention Centre"].lat) == (-79.28276, 43.72794)
    assert all(p.radius_m == 50 and p.premises_type == "Other" for p in places.values())


def test_inside_a_jail_is_left_out():
    assert at_excluded_place("Other", -79.51581, 43.61208 + 10 * METRE_LAT, [JAIL])


def test_outdoors_or_further_away_still_counts():
    assert not at_excluded_place("Outside", -79.51581, 43.61208, [JAIL])
    assert not at_excluded_place(None, -79.51581, 43.61208, [JAIL])  # homicides and shootings have no premises type
    assert not at_excluded_place("Other", -79.51581, 43.61208 + 100 * METRE_LAT, [JAIL])
    assert not at_excluded_place("Other", None, None, [JAIL])  # incidents without a location
