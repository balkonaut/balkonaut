import re
import time

from fastapi.testclient import TestClient

from app.main import app, de, path_length


def test_de():
    assert de(1234.5, 1) == "1.234,5"
    assert de(None) == "–"
    assert de(-0.01) == de(-0.0) == "0,0" and de(-0.06) == "-0,1"


def test_path_length():
    assert path_length("M300 144 V182 H210 V222") == 38 + 90 + 40
    assert path_length("M150 242 H124") == 26


def test_dashboard(client):
    assert "Noch keine Messwerte" in client.get("/").text  # leere Datenbank
    assert re.search(r"<footer>Balkonaut \d+\.\d+", client.get("/").text)  # Fußzeile mit Version
    now = int(time.time()) // 3600 * 3600
    storage = app.state.storage
    for t in range(now - 7200, now, 600):
        storage.add(t, {"grid_power": 300, "output_power": 200, "pv_power": 150, "battery_soc": 40, "battery_power": -100})
    storage.aggregate(now)
    r = client.get("/?zeitraum=gesamt")
    assert r.status_code == 200
    assert "40 %" in r.text and "Jetzt eintragen" in r.text
    assert "davon im Haus angekommen</span><b>0,2 kWh" in r.text  # Energiewege: 2 h Entladung mit 100 W
    assert client.get("/?zeitraum=unsinn").status_code == 200
    assert 'href="verlauf"' in r.text and 'href="/' not in r.text  # relativ, für Ingress


def test_regulation_page(client):
    assert "Noch keine Messwerte" in client.get("/nulleinspeisung").text
    now = int(time.time())
    for t in range(now - 600, now, 10):
        app.state.storage.add(t, {"grid_power": 20, "output_power": 300, "pv_ac_power": 0, "battery_soc": 50})
    page = client.get("/nulleinspeisung").text
    assert "100 %" in page and "Nach Uhrzeit" in page and "hilfe-uhrzeit" in page


def test_history_page(client):
    for view in ("tag", "woche", "monat", "jahr"):
        assert client.get(f"/verlauf?ansicht={view}").status_code == 200
    r = client.get("/verlauf?ansicht=monat&datum=2026-02-10")
    assert "Februar 2026" in r.text and "datum=2026-01-01" in r.text
    assert client.get("/verlauf?datum=unsinn").status_code == 200


def test_chart_ticks():
    from app.main import chart
    c = chart([{"own": 3.2, "grid": 15.4, "gen": 3.4}])  # Balken nebeneinander: Höchstwert ist der größte Einzelwert
    assert [t for t, _ in c["ticks"]] == [2, 4, 6, 8, 10, 12, 14] and c["ticks"][0][1] == "2" and c["forecast"] is None
    small = chart([{"own": 0.12, "grid": 0.2, "gen": 0, "fc": None}, {"own": 0, "grid": 0.1, "gen": 0.1, "fc": 0.25}])
    assert [label for _, label in small["ticks"]] == ["0,05", "0,10", "0,15", "0,20", "0,25"]
    assert small["forecast"] == "147.0,150.0 369.0,10.0"  # Mitte jedes Abschnitts, Prognose 0,25 kWh ganz oben
    assert chart([])["ticks"] == []


def test_api_v1(client):
    s = client.get("/api/v1/status").json()
    assert s["stand"] is None and s["live"] == {} and s["bilanz"]["tag"]["ersparnis"] == 0
    now = int(time.time())
    app.state.storage.add(now - 10, {"grid_power": 300, "output_power": 200, "battery_soc": 40})
    s = client.get("/api/v1/status").json()
    assert s["live"]["battery_soc"] == 40 and set(s["akku"]) == {"tag", "monat", "jahr", "gesamt"}
    v = client.get("/api/v1/verlauf?ansicht=woche").json()
    assert len(v["balken"]) == 7 and v["titel"].startswith("KW")
    assert client.get("/api/v1/nulleinspeisung").json()["regelbereit_stunden"] >= 0
    assert client.get("/api/bilanz").status_code == 404
    assert set(client.get("/api/v1/export").json()) == {"hourly", "regulation"}


def test_report(client):
    r = client.get("/bericht?monat=2026-02")
    assert r.status_code == 200 and "Monatsbericht Februar 2026" in r.text and "monat=2026-01" in r.text
    assert 'href="verlauf?ansicht=tag&amp;datum=2026-02-28"' in r.text  # Tagesbalken öffnen den Tag im Verlauf
    assert client.get("/bericht?monat=unsinn").status_code == 200
    j = client.get("/api/v1/bericht?monat=2026-02").json()
    assert len(j["tage"]) == 28 and j["vorjahr"]["ersparnis"] == 0


def test_store_regulation_days(client):
    from datetime import datetime, timedelta
    from balkonaut.views import store_regulation_days
    from balkonaut.analytics import TZ
    storage = app.state.storage
    yesterday = datetime.now(TZ).date() - timedelta(days=1)
    t0 = int(datetime.combine(yesterday, datetime.min.time(), TZ).timestamp())
    for t in range(t0, t0 + 3600, 10):
        storage.add(t, {"grid_power": 20, "output_power": 300, "pv_ac_power": 0, "battery_soc": 50})
    store_regulation_days(storage, {"energy": 0.3, "feed_in": 0}, datetime.now(TZ).timestamp())
    days = storage.regulation_days(yesterday.isoformat(), yesterday.isoformat())
    assert days[yesterday.isoformat()]["anteil_nahe_null"] == 1
    r = client.get(f"/api/v1/bericht?monat={yesterday:%Y-%m}").json()
    assert r["nulleinspeisung"]["tage"] == 1


def test_store_regulation_days_dst(client):
    from datetime import datetime
    from balkonaut.views import store_regulation_days
    from balkonaut.analytics import TZ
    storage = app.state.storage
    t0 = int(datetime(2026, 10, 25, 23, tzinfo=TZ).timestamp())  # letzte Stunde des 25-Stunden-Tags
    for t in range(t0, t0 + 3600, 10):
        storage.add(t, {"grid_power": 20, "output_power": 300, "pv_ac_power": 0, "battery_soc": 50})
    store_regulation_days(storage, {"energy": 0.3, "feed_in": 0}, datetime(2026, 10, 26, 12, tzinfo=TZ).timestamp())
    assert "2026-10-25" in storage.regulation_days("2026-10-25", "2026-10-25")


def test_soc_gauge():
    from app.main import soc_gauge
    assert soc_gauge({}) is None
    g = soc_gauge({"battery_soc": 10, "battery_soc_min": 10, "battery_soc_max": 95, "battery_discharge_protection": 12})
    assert g["hue"] == 0 and [m["key"] for m in g["marks"]] == ["lo", "prot", "hi"]
    assert soc_gauge({"battery_soc": 95, "battery_soc_min": 10, "battery_soc_max": 95})["hue"] == 130
    g = soc_gauge({"battery_soc": 50})  # ohne Grenzen: 0 bis 100 %
    assert g["hue"] == 65 and g["marks"] == []
    top = soc_gauge({"battery_soc": 1, "battery_soc_max": 25})["marks"][0]  # 25 % liegt im gedrehten Ring rechts
    assert (top["x1"], top["y1"]) == (50, 84)
    live = {"battery_soc": 50, "battery_soc_min": 10, "battery_soc_max": 95, "battery_capacity": 6.0}
    assert soc_gauge({**live, "battery_power": 600})["rest"] == {"target": 95, "minutes": 270}  # 2,7 kWh mit 0,6 kW
    assert soc_gauge({**live, "battery_power": -600, "battery_discharge_protection": 12})["rest"]["target"] == 12
    assert soc_gauge({**live, "battery_power": 5})["rest"] is None  # ruht
    assert soc_gauge({**live, "battery_soc": 96, "battery_power": 300})["rest"] is None  # über der Grenze


def test_flow_inverters(client):
    now = int(time.time())
    app.state.storage.add(now - 10, {"pv_power": 400, "battery_soc": 50})
    page = client.get("/").text
    assert "Zusatz-WR" not in page and ">Wechselrichter</text>" in page  # nur ein Wechselrichter, ohne Gerät neutral
    app.state.storage.add(now - 5, {"pv_power": 400, "pv_ac_power": 300, "battery_soc": 50})
    assert "Zusatz-WR" in client.get("/").text


def test_flow_module_labels(client, tmp_path):
    """Modulfelder tragen die Ausrichtung der Flächen am jeweiligen Wechselrichter."""
    (tmp_path / "config.yaml").write_text(
        "location: {lat: 50, lon: 10}\nplanes:\n  - {declination: 30, azimuth: 150, kwp: 0.87, inverter: storage}\n"
        "  - {declination: 30, azimuth: 251, kwp: 0.87, inverter: extra}\n")
    app.state.storage.add(int(time.time()) - 5, {"pv_power": 400, "pv_ac_power": 300, "battery_soc": 50})
    page = client.get("/").text
    assert ">Südost</text>" in page and ">West</text>" in page  # 251° liegt näher an West (270°) als an Südwest


def test_flow_names(client, tmp_path):
    """Mitte heißt wie der Speicher-Wechselrichter, der Akku wie in den Einstellungen eingetragen."""
    (tmp_path / "config.yaml").write_text("devices:\n  - {type: apsystems_ezhi, host: 10.0.0.11}\n"
                                          "system: {cost: 0, commissioned: null, battery_name: Phylion, extra_name: EZ1-M}\n")
    app.state.storage.add(int(time.time()) - 5, {"pv_power": 400, "pv_ac_power": 300, "battery_power": 200, "battery_soc": 50})
    page = client.get("/").text
    assert ">EZHI</text>" in page and ">Phylion lädt</text>" in page and ">EZ1-M</text>" in page
