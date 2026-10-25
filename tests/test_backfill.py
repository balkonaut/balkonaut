from balkonaut.homeassistant import HomeAssistant
from balkonaut.storage import Storage

H = 3600 * 1000


def test_backfill_keeps_existing_hours():
    s = Storage(":memory:")
    s.db.execute("INSERT INTO hourly VALUES ('grid_power', ?, 999, 999, 0, NULL, 1)", (H + 3600,))
    series = {"grid_power": [(H - 5, 100.0), (H + 1800, -100.0)], "battery_soc": [(H, 50.0)]}
    assert s.backfill(series, H, H + 7200) == 2
    rows = dict(((k, h), (m, pos, neg)) for k, h, m, pos, neg, *_ in s.db.execute("SELECT * FROM hourly"))
    assert rows[("grid_power", H)] == (0, 50, -50)  # halbe Stunde +100, halbe Stunde -100
    assert rows[("grid_power", H + 3600)] == (999, 999, 0)  # vorhandene Stunde unverändert
    assert s.first() == H


def test_history(monkeypatch):
    ha = HomeAssistant("http://ha", "t", {"grid_power": ("sensor.g", -1)})
    def fake_get(path, timeout=10):
        if path.startswith("/api/states/"):
            return {"state": "1", "attributes": {"unit_of_measurement": "kW"}}
        return [[{"entity_id": "sensor.g", "state": "2", "last_changed": "2026-10-10T10:00:00+00:00"},
                 {"state": "unavailable", "last_changed": "2026-10-10T10:05:00+00:00"}]]
    monkeypatch.setattr(ha, "_get", fake_get)
    h = ha.history(0, 86400)
    assert h == {"grid_power": [(1791626400.0, -2000.0), (1791626700.0, None)]}


def test_backfill_like_sampling():
    """Gleiches Ergebnis wie das Abtasten im 10-s-Raster über den Collector-Weg (add + aggregate)."""
    import bisect
    import random
    rnd = random.Random(1)
    start, until = H - 1800, H + 3 * 3600  # Beginn mitten in der Stunde
    t, points = start - 300.5, []
    while t < until:
        points.append((t, rnd.choice([None, rnd.uniform(-500, 800)])))
        t += rnd.uniform(1, 900)
    series = {"grid_power": points, "battery_soc": [(start + 7, 40.0), (start + 5000, 41.0)]}
    ref = Storage(":memory:")
    for t in range(start, until, 10):
        ref.add(t, {k: s[i][1] for k, s in series.items() if (i := bisect.bisect_right([p[0] for p in s], t) - 1) >= 0})
    ref.aggregate(until)
    s = Storage(":memory:")
    s.backfill(series, start, until)
    got = s.db.execute("SELECT * FROM hourly ORDER BY key, hour").fetchall()
    want = ref.db.execute("SELECT * FROM hourly ORDER BY key, hour").fetchall()
    assert len(got) == len(want) and all(
        g[:2] == w[:2] and g[5:] == w[5:] and all(abs(x - y) < 1e-6 for x, y in zip(g[2:5], w[2:5])) for g, w in zip(got, want))
