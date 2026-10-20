from datetime import datetime

from balkonaut.analytics import TZ, amortization, balance, battery, periods

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
    assert abs(a["ersparnis_pro_jahr"] - 0.6 / 2 * 365.25) < 1e-9
    assert abs(a["jahre_bis_amortisation"] - (500 - 30.6) / (0.3 * 365.25)) < 1e-9


def test_periods():
    p = periods(datetime(2026, 10, 20, 14, 0, tzinfo=TZ).timestamp())
    assert p["tag"] == datetime(2026, 10, 20, tzinfo=TZ).timestamp()
    assert p["monat"] == datetime(2026, 10, 1, tzinfo=TZ).timestamp()
    assert p["jahr"] == datetime(2026, 1, 1, tzinfo=TZ).timestamp()


def test_battery():
    rows = []
    for h in range(3):
        t = h * 3600
        rows += [("battery_capacity", t, 5.0, 5.0, 0, 5.0),
                 ("battery_soc", t, [95, 50, 10][h], [95, 50, 10][h], 0, [95, 50, 10][h]),
                 ("battery_soc_max", t, 95, 95, 0, 95), ("battery_soc_min", t, 10, 10, 0, 10),
                 ("battery_soh", t, 99, 99, 0, 99),
                 ("battery_charge_energy", t, 0, 0, 0, [100.0, 101.0, 101.0][h]),
                 ("battery_discharge_energy", t, 0, 0, 0, [50.0, 51.0, 54.0][h]),
                 ("grid_power", t, 0, [0, 0, 800][h], [-300, 0, 0][h], None)]
    b = battery(sorted(rows), 0, PRICES)
    assert b["zyklen"] == 4 / 5 and b["zyklen_gesamt"] == 54 / 5 and b["gesundheit"] == 99
    assert abs(b["wirkungsgrad"] - (4 + (10 - 95) / 100 * 5) / 1) < 1e-9
    assert (b["stunden_voll"], b["einspeisung_bei_vollem_akku"]) == (1, 0.3)
    assert (b["stunden_leer"], b["netzbezug_bei_leerem_akku"]) == (1, 0.8)
    assert battery([], 0, PRICES)["zyklen"] is None  # ohne Daten


def test_amortization_with_commissioning():
    from datetime import date
    end = datetime(2026, 10, 20, tzinfo=TZ).timestamp()
    rows = [("output_energy", end - 7200, 1, 1, 0, 730.0), ("output_energy", end - 3600, 1, 1, 0, 730.5)]
    a = amortization(rows, PRICES, cost=500, commissioned=date(2025, 10, 20))  # genau ein Jahr
    assert a["basis"] == "inbetriebnahme" and a["zaehler_plausibel"]
    assert abs(a["ersparnis_pro_jahr"] / a["bisher_gespart"] - 1) < 0.001  # ein Jahr: Jahresersparnis = bisher
    assert a["amortisiert_am"] > date(2026, 10, 20)
    assert not amortization(rows, PRICES, 500, date(2026, 10, 1))["zaehler_plausibel"]  # 730 kWh in 19 Tagen


def test_regulation():
    from balkonaut.analytics import regulation
    series = {}
    for i in range(10):  # Akku über Untergrenze, eigener Anteil 200 W unter Limit 800 W
        series[i * 10] = {"grid_power": 10, "output_power": 300, "pv_ac_power": 100, "battery_soc": 50}
    series[100] = {"grid_power": 610, "output_power": 300, "pv_ac_power": 100, "battery_soc": 50}  # Lastsprung
    series[110] = {"grid_power": 200, "output_power": 700, "pv_ac_power": 100, "battery_soc": 50}
    series[120] = {"grid_power": 20, "output_power": 900, "pv_ac_power": 100, "battery_soc": 50}  # am Limit
    series[130] = {"grid_power": -100, "output_power": 300, "pv_ac_power": 0, "battery_soc": 5}  # Akku leer
    r = regulation(series, PRICES)
    assert r["lastspruenge"] == 1 and r["reaktionszeit_median"] == 20 and r["nicht_ausgeregelt"] == 0
    assert r["anteil_nahe_null"] == 10 / 12  # 12 regelbereite Messungen, 10 davon nahe 0
    assert abs(r["einspeisung"] - 100 * 10 / 3600 / 1000) < 1e-12
    assert abs(r["vermeidbarer_netzbezug"] - (10 * 10 + 600 + 200) * 10 / 3600 / 1000) < 1e-12
    assert r["max_abgabe"] == 900 and r["anteil_ueber_limit"] == 1 / 14
    assert regulation({}, PRICES) is None


def test_buckets():
    from datetime import date
    from balkonaut.analytics import buckets
    title, bars, prev, nxt = buckets("tag", date(2026, 10, 25))  # Ende der Sommerzeit: 25 Stunden
    assert len(bars) == 25 and bars[0][0] == "00" and prev == date(2026, 10, 24)
    title, bars, prev, nxt = buckets("woche", date(2026, 10, 21))
    assert title == "KW 43/2026" and bars[0][0] == "Mo 19." and nxt == date(2026, 10, 26)
    title, bars, prev, nxt = buckets("monat", date(2026, 2, 10))
    assert len(bars) == 28 and prev == date(2026, 1, 1) and nxt == date(2026, 3, 1)
    title, bars, prev, nxt = buckets("jahr", date(2026, 5, 5))
    assert len(bars) == 12 and bars[0][0] == "Jan" and title == "2026"


def test_expected_share_and_profile():
    from balkonaut.analytics import expected_share
    profile = [10] * 6 + [30] * 6  # zweites Halbjahr dreimal so ertragreich
    start = datetime(2026, 1, 1, tzinfo=TZ).timestamp()
    assert abs(expected_share(start, datetime(2027, 1, 1, tzinfo=TZ).timestamp(), profile) - 1) < 1e-9
    assert abs(expected_share(start, datetime(2026, 2, 1, tzinfo=TZ).timestamp(), profile) - 10 / 240) < 1e-9
    rows = [("output_energy", h * 3600, 0, 0, 0, 1.0 + h * 0.01) for h in range(int(start // 3600), int(start // 3600) + 24 * 31)]
    a = amortization(rows, PRICES, 500, profile=profile)  # Januar gemessen
    flat = amortization(rows, PRICES, 500)
    assert a["jahresverlauf"] and a["erwarteter_ertrag_jahr"] == 240
    # Januar bringt laut Profil 10/240 des Jahres, nach Tagen wären es 31/365,25
    assert abs(a["ersparnis_pro_jahr"] / flat["ersparnis_pro_jahr"] - (240 / 10) / (365.25 / 31)) < 1e-9


def test_yield_watch():
    from balkonaut.analytics import yield_watch
    day0 = datetime(2026, 10, 10, tzinfo=TZ).timestamp()
    rows = []
    for h in range(24 * 8):  # 8 Tage, gewertet werden die 7 vollen Tage vor dem 18.10.
        t = day0 + h * 3600
        rows += [("pv_forecast_today", t, 2.0, 2.0, 0, 2.0), ("pv_ac_forecast_today", t, 2.0, 2.0, 0, 2.0),
                 ("pv_energy", t, 0, 0, 0, 100 + h * 2.0 / 24),  # Speicher: 2 kWh am Tag = 100 %
                 ("pv_ac_power", t, 1.0 / 24 * 1000, 0, 0, None)]  # zweiter: 1 kWh am Tag = 50 %
    w = yield_watch(sorted(rows), datetime(2026, 10, 18, 12, tzinfo=TZ).timestamp())
    assert abs(w["wechselrichter"]["speicher"]["quote"] - 1) < 0.01
    assert abs(w["wechselrichter"]["ac"]["quote"] - 0.5) < 0.01
    assert {x["code"] for x in w["warnungen"]} == {"ertrag_niedrig", "ungleich"}
    assert all(x["wechselrichter"] == "ac" for x in w["warnungen"])
    assert yield_watch([], 0)["warnungen"] == []


def test_combine_regulation():
    from balkonaut.analytics import combine_regulation
    day = {"zeitraum_stunden": 24, "regelbereit_stunden": 6, "anteil_nahe_null": 0.5, "median_netz": 40,
           "vermeidbarer_netzbezug": 0.2, "vermeidbare_kosten": 0.06, "einspeisung": 0.1, "einspeisung_wert": 0.03,
           "lastspruenge": 3, "reaktionszeit_median": 30, "nicht_ausgeregelt": 1, "limit": 800, "max_abgabe": 900,
           "anteil_ueber_limit": 0.1}
    other = day | {"regelbereit_stunden": 2, "anteil_nahe_null": 1.0, "reaktionszeit_median": None, "max_abgabe": 700}
    c = combine_regulation([day, other])
    assert c["tage"] == 2 and c["regelbereit_stunden"] == 8 and c["lastspruenge"] == 6
    assert c["anteil_nahe_null"] == (0.5 * 6 + 1.0 * 2) / 8 and c["max_abgabe"] == 900 and c["reaktionszeit_median"] == 30
    assert combine_regulation([]) is None
