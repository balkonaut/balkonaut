import time

from fastapi.testclient import TestClient

from app.main import app, de


def test_de():
    assert de(1234.5, 1) == "1.234,5"
    assert de(None) == "–"


def test_dashboard(client):
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


def test_regulation_page(client):
    assert "Noch keine Messwerte" in client.get("/nulleinspeisung").text
    now = int(time.time())
    for t in range(now - 600, now, 10):
        app.state.storage.add(t, {"grid_power": 20, "output_power": 300, "pv_ac_power": 0, "battery_soc": 50})
    assert "100 %" in client.get("/nulleinspeisung").text


def test_history_page(client):
    for view in ("tag", "woche", "monat", "jahr"):
        assert client.get(f"/verlauf?ansicht={view}").status_code == 200
    r = client.get("/verlauf?ansicht=monat&datum=2026-02-10")
    assert "Februar 2026" in r.text and "datum=2026-01-01" in r.text
    assert client.get("/verlauf?datum=unsinn").status_code == 200


def test_chart_ticks():
    from app.main import chart
    c = chart([{"own": 3.2, "grid": 15.4, "gen": 3.4}])
    assert [t for t, _ in c["ticks"]] == [5, 10, 15] and c["ticks"][0][1] == "5"
    assert [label for _, label in chart([{"own": 0.12, "grid": 0.2, "gen": 0}])["ticks"]] == ["0,1", "0,2", "0,3"]
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


def test_report(client):
    r = client.get("/bericht?monat=2026-02")
    assert r.status_code == 200 and "Monatsbericht Februar 2026" in r.text and "monat=2026-01" in r.text
    assert client.get("/bericht?monat=unsinn").status_code == 200
    j = client.get("/api/v1/bericht?monat=2026-02").json()
    assert len(j["tage"]) == 28 and j["vorjahr"]["ersparnis"] == 0
