import yaml
from fastapi.testclient import TestClient

from app.main import app


def test_settings_roundtrip(client, tmp_path):
    assert client.get("/einstellungen").status_code == 200
    r = client.post("/einstellungen", data={"energy": "0,32", "feed_in": "0", "cost": "1499"}, follow_redirects=False)
    assert r.status_code == 303
    assert client.post("/einstellungen", data={"energy": "-1", "feed_in": "0", "cost": "0"}).status_code == 400
    assert "Gespeichert" in client.get("/einstellungen?gespeichert=1").text
    cfg = yaml.safe_load((tmp_path / "config.yaml").read_text())
    assert cfg == {"prices": {"energy": 0.32, "feed_in": 0.0}, "system": {"cost": 1499.0, "commissioned": None, "battery_name": None}}


def test_settings_commissioned(client):
    form = {"energy": "0.3", "feed_in": "0", "cost": "1450"}
    assert client.post("/einstellungen", data=form | {"commissioned": "2099-01-01"}).status_code == 400
    client.post("/einstellungen", data=form | {"commissioned": "2024-05-01"})
    assert 'value="2024-05-01"' in client.get("/einstellungen").text
    assert client.get("/").status_code == 200


def test_addon(client, tmp_path, monkeypatch):
    import json
    from app import config
    monkeypatch.setenv("SUPERVISOR_TOKEN", "abc")
    form = {"energy": "0.3", "feed_in": "0", "cost": "1450"}
    assert client.post("/einstellungen", data=form).status_code == 403  # nicht über Ingress
    assert ":8000</code>" in client.get("/einstellungen").text  # Adresse für die Integration
    (tmp_path / "options.json").write_text(json.dumps({"entities": {"grid_power": "sensor.netz", "pv_power": ""},
                                                        "invert": ["grid_power"]}))
    cfg = config.load(tmp_path / "config.yaml")
    assert cfg["home_assistant"] == {"url": "http://supervisor/core", "token": "abc",
                                     "entities": {"grid_power": ["sensor.netz", -1]}}
    config.save(tmp_path / "config.yaml", cfg)
    assert "home_assistant" not in yaml.safe_load((tmp_path / "config.yaml").read_text())


def test_devices_and_planes(client, tmp_path, monkeypatch):
    """Gerät per IP hinzufügen (Typ erkannt), Richtung drehen, entfernen; Standort und Flächen speichern."""
    from balkonaut import devices
    monkeypatch.setattr(devices, "detect", lambda host: {"10.0.0.38": "shelly_plug"}.get(host) or (_ for _ in ()).throw(ValueError()))
    monkeypatch.setitem(devices.TYPES, "shelly_plug", lambda host: {"output_power": -21.0, "output_energy": 1612.4})
    assert "Jetzt einrichten" in client.get("/").text
    assert "antwortet kein bekanntes Gerät" in client.post("/einstellungen", data={"bereich": "geraete", "aktion": "hinzufuegen", "host": "10.0.0.99"}).text
    r = client.post("/einstellungen", data={"bereich": "geraete", "aktion": "hinzufuegen", "host": "10.0.0.38"})
    assert str(r.url).endswith("/einstellungen?gespeichert=1#geraete") and "Gespeichert." in r.text  # gleiche Adresse
    page = client.get("/einstellungen").text
    assert "Shelly Plug" in page and "Abgabe 21 W (Bezug, Vorzeichen prüfen)" in page
    client.post("/einstellungen", data={"bereich": "geraete", "aktion": "drehen", "host": "10.0.0.38"})
    assert "Abgabe 21 W ·" in client.get("/einstellungen").text
    cfg = yaml.safe_load((tmp_path / "config.yaml").read_text())
    assert cfg["devices"] == [{"type": "shelly_plug", "host": "10.0.0.38", "invert": ["output_power"]}]
    assert "Jetzt einrichten" not in client.get("/").text

    form = {"lat": "50,1", "lon": "8,7", "declination": ["30", ""], "azimuth": ["150", ""], "kwp": ["0,87", ""],
            "inverter": ["storage", "storage"]}
    assert client.post("/einstellungen", data={"bereich": "flaechen"} | form, follow_redirects=False).status_code == 303
    cfg = yaml.safe_load((tmp_path / "config.yaml").read_text())
    assert cfg["location"] == {"lat": 50.1, "lon": 8.7}
    assert cfg["planes"] == [{"declination": 30.0, "azimuth": 150.0, "kwp": 0.87, "inverter": "storage"}]
    r = client.post("/einstellungen", data={"bereich": "flaechen"} | form | {"lat": "", "lon": "", "azimuth": ["400", ""]})
    assert r.status_code == 400 and "Fläche 1, Ausrichtung: 0 bis 360" in r.text and "fehlt der Standort" in r.text
    assert 'value="400"' in r.text  # Eingaben bleiben stehen

    client.post("/einstellungen", data={"bereich": "geraete", "aktion": "entfernen", "host": "10.0.0.38"})
    assert "devices" not in yaml.safe_load((tmp_path / "config.yaml").read_text())
