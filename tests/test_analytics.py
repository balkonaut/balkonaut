from datetime import datetime

from balkonaut.analytics import TZ, amortization, balance, periods

PRICES = {"energy": 0.30, "feed_in": 0.10}


def test_balance():
    rows = [  # zwei Stunden; Zähler mit Basiswert vor dem Zeitraum
        ("grid_power", 3600, 400, 500, -100, None),
        ("grid_power", 7200, 1000, 1000, 0, None),
        ("output_energy", 0, 10.0, 10.0, 0, 10.0),
        ("output_energy", 3600, 10.5, 10.5, 0, 10.5),
        ("output_energy", 7200, 11.0, 11.0, 0, 11.0),
        ("pv_ac_power", 3600, 200, 200, 0, None),
        ("pv_energy", 3600, 5.0, 5.0, 0, 5.0),
        ("pv_energy", 7200, 5.8, 5.8, 0, 5.8),
    ]
    b = balance(rows, 3600, PRICES)
    assert b["netzbezug"] == 1.5 and b["einspeisung"] == 0.1
    assert b["abgabe"] == 1.0 and b["eigenverbrauch"] == 0.9
    assert abs(b["erzeugung"] - 1.0) < 1e-9  # 0,8 kWh Zähler (erste Stunde ohne Basis) + 0,2 kWh
    assert b["hausverbrauch"] == 2.4
    assert abs(b["ersparnis"] - (0.9 * 0.30 + 0.1 * 0.10)) < 1e-9
    assert b["eigenverbrauchsquote"] == 0.9


def test_balance_without_counter_and_reset():
    rows = [("output_energy", 0, 50.0, 50.0, 0, 50.0), ("output_energy", 3600, 0.2, 0.2, 0, 0.2),
            ("output_power", 3600, 300, 300, 0, None)]
    assert balance(rows, 0, PRICES)["abgabe"] == 0  # Rücksetzung zählt nicht
    assert balance([rows[2]], 0, PRICES)["abgabe"] == 0.3  # ohne Zähler: Leistung


def test_amortization():
    rows = [("grid_power", h * 3600, 0, 0, 0, None) for h in range(48)]
    rows += [("output_energy", 0, 100.0, 100.0, 0, 100.0), ("output_energy", 47 * 3600, 102.0, 102.0, 0, 102.0)]
    a = amortization(rows, PRICES, cost=500)
    assert a["messtage"] == 2
    assert abs(a["bisher_gespart"] - 102 * 0.30) < 1e-9
    assert abs(a["ersparnis_pro_jahr"] - 0.6 / 2 * 365) < 1e-9
    assert abs(a["jahre_bis_amortisation"] - (500 - 30.6) / (0.3 * 365)) < 1e-9


def test_periods():
    p = periods(datetime(2026, 10, 20, 14, 0, tzinfo=TZ).timestamp())
    assert p["tag"] == datetime(2026, 10, 20, tzinfo=TZ).timestamp()
    assert p["monat"] == datetime(2026, 10, 1, tzinfo=TZ).timestamp()
    assert p["jahr"] == datetime(2026, 1, 1, tzinfo=TZ).timestamp()
