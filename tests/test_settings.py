import yaml
from fastapi.testclient import TestClient

from app.main import app


def test_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("BALKONAUT_DATA", str(tmp_path))
    with TestClient(app) as client:
        assert client.get("/einstellungen").status_code == 200
        r = client.post("/einstellungen", data={"energy": "0,32", "feed_in": "0", "cost": "1499"}, follow_redirects=False)
        assert r.status_code == 303
        assert client.post("/einstellungen", data={"energy": "-1", "feed_in": "0", "cost": "0"}).status_code == 400
        assert "Gespeichert" in client.get("/einstellungen?gespeichert=1").text
    cfg = yaml.safe_load((tmp_path / "config.yaml").read_text())
    assert cfg == {"prices": {"energy": 0.32, "feed_in": 0.0}, "system": {"cost": 1499.0, "commissioned": None}}


def test_settings_commissioned(tmp_path, monkeypatch):
    monkeypatch.setenv("BALKONAUT_DATA", str(tmp_path))
    with TestClient(app) as client:
        form = {"energy": "0.3", "feed_in": "0", "cost": "1450"}
        assert client.post("/einstellungen", data=form | {"commissioned": "2099-01-01"}).status_code == 400
        client.post("/einstellungen", data=form | {"commissioned": "2024-05-01"})
        assert 'value="2024-05-01"' in client.get("/einstellungen").text
        assert client.get("/").status_code == 200
