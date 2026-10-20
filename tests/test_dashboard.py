import time

from fastapi.testclient import TestClient

from app.main import app, de


def test_de():
    assert de(1234.5, 1) == "1.234,5"
    assert de(None) == "–"


def test_dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv("BALKONAUT_DATA", str(tmp_path))
    with TestClient(app) as client:
        assert "Noch keine Messwerte" in client.get("/").text  # leere Datenbank
        now = int(time.time()) // 3600 * 3600
        storage = app.state.storage
        for t in range(now - 7200, now, 600):
            storage.add(t, {"grid_power": 300, "output_power": 200, "pv_power": 150, "battery_soc": 40})
        storage.aggregate(now)
        r = client.get("/?zeitraum=gesamt")
        assert r.status_code == 200
        assert "40 %" in r.text and "Jetzt eintragen" in r.text
        assert client.get("/?zeitraum=unsinn").status_code == 200
