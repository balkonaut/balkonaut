from balkonaut.storage import RAW_DAYS, Storage

H = 3600 * 1000  # beliebige volle Stunde


def test_aggregate():
    s = Storage(":memory:")
    for i, v in enumerate([100, -50, 300, -50]):  # vier Werte in der ersten Stunde
        s.add(H + i * 900, {"grid_power": v, "battery_soc": 10 + i, "pv_power": None})
    s.add(H + 3600, {"grid_power": 7})  # angefangene zweite Stunde
    s.aggregate(H + 3600 + 10)
    rows = s.db.execute("SELECT key, hour, mean, mean_pos, mean_neg, last, n FROM hourly ORDER BY key").fetchall()
    assert rows == [("battery_soc", H, 11.5, 11.5, 0, 13, 4),
                    ("grid_power", H, 75, 100, -25, -50, 4)]
    s.aggregate(H + 3600 + 20)  # nichts Neues, keine Doppelzählung
    assert s.db.execute("SELECT count(*) FROM hourly").fetchone() == (2,)
    s.aggregate(H + 2 * 3600 + RAW_DAYS * 86400)  # zweite Stunde aggregieren, alte Rohwerte löschen
    assert s.db.execute("SELECT count(*) FROM raw").fetchone() == (0,)
    assert s.db.execute("SELECT mean FROM hourly WHERE hour = ?", (H + 3600,)).fetchone() == (7,)
