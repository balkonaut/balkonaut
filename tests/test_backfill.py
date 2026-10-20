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
