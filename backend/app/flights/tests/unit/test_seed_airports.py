"""Row building of the airport load (the database part runs with `make seed-airports`)."""

from app.flights.commands.seed_airports import airport_rows, city_rows, importance


def large(scheduled="yes", type_="large_airport", keywords=""):
    return {"scheduled_service": scheduled, "type": type_, "keywords": keywords}


def test_importance():
    assert importance(large()) == 4
    assert importance(large(type_="medium_airport")) == 3
    assert importance(large(type_="small_airport")) == 2
    assert importance(large(type_="seaplane_base")) == 1
    assert importance(large(scheduled="no")) == 0
    assert importance(None) == 0


def test_airports_link_to_their_multi_airport_city_and_keep_alternative_names():
    rows = {r["iata_code"]: r for r in airport_rows({"LHR": large(keywords="LON, Londres")})}

    lhr = rows["LHR"]
    assert lhr["city_code"] == "LON"
    assert lhr["time_zone"] == "Europe/London"
    assert lhr["importance"] == 4
    assert "londres" in lhr["search_text"]
    assert rows["JFK"]["city_code"] == "NYC"
    assert rows["JFK"]["importance"] == 0  # not in the given OurAirports data
    assert len(rows) > 7000


def test_cities():
    rows = {r["iata_code"]: r for r in city_rows()}

    assert rows["NYC"]["name"] == "New York"
    assert rows["BUE"]["search_text"] == "bue buenos aires"
