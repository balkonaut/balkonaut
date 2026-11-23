from datetime import datetime
from dataclasses import replace

from balkonaut.simulate import Anlage, calibrate, hours, measured, simulate

# Ein Tag: mittags 1000 W Sonne bei 200 W Haus, abends 400 W Haus ohne Sonne
DAY = [(h * 3600, 1000.0 if 10 <= h < 14 else 0.0, 400.0 if 18 <= h < 22 else 200.0) for h in range(24)]


def test_without_battery():
    r = simulate(DAY, Anlage(limit=800))
    assert r["einspeisung"] == 4 * 0.6  # bis zum Limit von 800 W, 200 W gehen ins Haus
    assert r["abgeregelt"] == 4 * 0.2
    assert r["netzbezug"] == 20 * 0.2 + 4 * 0.2


def test_battery_shifts_surplus_to_evening():
    a = Anlage(capacity=2, soc_min=10, soc_max=100, efficiency=1)
    r = simulate(DAY, a)
    # voll bei 2 kWh (ab 10 %); abends 4 × 400 W, der Rest reicht für eine Nachtstunde mit 200 W
    assert r["geladen"] == r["entladen"] == 1.8
    # Überschuss 3,2 kWh: 1,8 in den Akku, 1,2 ins Netz (Limit 800 W abzüglich 200 W Haus), 0,2 abgeregelt
    assert (round(r["einspeisung"], 9), round(r["abgeregelt"], 9)) == (1.2, 0.2)
    assert round(r["netzbezug"], 9) == 3.0  # 16 × 0,2 + 4 × 0,4 − 1,8


def test_charge_first_and_calibrate():
    a = Anlage(capacity=10, efficiency=1)
    plain, first = simulate(DAY, a), simulate(DAY, replace(a, charge_first=0.5))
    assert first["geladen"] == plain["geladen"] + 4 * 0.1  # die Hälfte der direkt nutzbaren 200 W
    assert calibrate(DAY, a, first["geladen"]) == 0.5
    assert calibrate(DAY, Anlage(), 3.0) == 0.0  # ohne Akku kein Ladevorrang


def test_hours_and_measured():
    rows = [("grid_power", 0, 300.0, 300.0, 0.0, None), ("output_power", 0, 100.0, 100.0, 0.0, None),
            ("pv_power", 0, 150.0, 150.0, 0.0, None), ("battery_power", 0, 50.0, 50.0, 0.0, None),
            ("grid_power", 3600, 100.0, 100.0, 0.0, None)]  # ohne Abgabe: Stunde fehlt
    assert hours(rows) == [(0, 150.0, 400.0)]
    assert measured(rows, 0, 7200) == {"netzbezug": 0.3, "einspeisung": 0.0, "ins_haus": 0.1, "geladen": 0.05,
                                       "entladen": 0.0}


def test_year_and_battery_options():
    from datetime import date
    from zoneinfo import ZoneInfo

    from balkonaut.simulate import battery_options, days, year
    tz = ZoneInfo("Europe/Berlin")
    t0 = int(datetime(2026, 11, 2, tzinfo=tz).timestamp())
    series = [(t0 + i * 3600, pv, house) for i, (_, pv, house) in enumerate(DAY * 2)]
    measured_days = days(series[:-1], tz)  # zweiter Tag unvollständig
    assert [d for d, *_ in measured_days] == [date(2026, 11, 2)]
    y = year(measured_days, [150.0] * 6 + [300.0] * 6, 51.0, 10.0, tz)
    assert len(y) == 365 * 24
    assert round(sum(pv for _, pv, _ in y) / 1000) == 6 * 150 + 6 * 300  # PV je Monat wie im Profil
    pv_june = [pv for t, pv, _ in y[24 * 160:24 * 161]]
    assert pv_june[3] == 0 and pv_june[13] > 0  # nachts keine Sonne
    opts = battery_options(y, Anlage(capacity=2), {"energy": 0.3}, [0, 2, 4])
    assert opts[1]["mehr"] == 0 and opts[0]["mehr"] < 0 < opts[2]["mehr"]
    assert abs(opts[0]["ersparnis"] - opts[0]["ins_haus"] * 0.3) < 1e-9
