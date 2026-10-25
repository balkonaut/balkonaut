from balkonaut.homeassistant import HomeAssistant, normalize


def state(value, unit):
    return {"state": value, "attributes": {"unit_of_measurement": unit}}


def test_normalize():
    assert normalize(state("1.5", "kW")) == 1500
    assert normalize(state("250", "Wh")) == 0.25
    assert normalize(state("-96", "W"), -1) == 96
    assert normalize(state("11", "%")) == 11
    assert normalize(state("unavailable", "W")) is None
    assert normalize(None) is None


def test_read(monkeypatch):
    states = {"sensor.grid": state("570.4", "W"), "sensor.out": state("-96", "W")}
    ha = HomeAssistant("http://ha:8123/", "t", {"grid_power": ("sensor.grid", 1),
                                                "output_power": ("sensor.out", -1),
                                                "battery_soc": ("sensor.missing", 1)})
    monkeypatch.setattr(ha, "_state", states.get)
    assert ha.read() == {"grid_power": 570.4, "output_power": 96, "battery_soc": None}


def test_solar_planes(monkeypatch):
    ha = HomeAssistant("http://ha", "t", {})
    answers = {
        "/api/config/config_entries/entry?domain=forecast_solar": [{"entry_id": "a"}],
        "/api/diagnostics/config_entry/a": {"data": {"entry": {"subentries": [
            {"data": {"declination": 30, "azimuth": 150, "modules_power": 870}}]}}},
        "/api/config": {"latitude": 50.0, "longitude": 10.0},
    }
    monkeypatch.setattr(ha, "_get", lambda path, timeout=10: answers[path])
    assert ha.solar_planes() == (50.0, 10.0, [(30, 150, 0.87)])


def test_planes_without_forecast_solar(monkeypatch):
    """Eingetragene Flächen: Prognose selbst abgerufen, Standort aus Home Assistant, zugeordnete Entität geht vor."""
    from balkonaut import forecast
    monkeypatch.setattr(forecast, "estimate", lambda lat, lon, tilt, azimuth, kwp: ({150: 4.2, 251: 3.1}[azimuth] * (lat == 50.0), {}))
    planes = [{"declination": 30, "azimuth": 150, "kwp": 0.87, "inverter": "storage"},
              {"declination": 30, "azimuth": 251, "kwp": 0.87, "inverter": "extra"}]
    ha = HomeAssistant("http://ha", "t", {"pv_ac_forecast_today": ("sensor.prognose", 1)}, None, planes)
    monkeypatch.setattr(ha, "_get", lambda path, timeout=10: {"/api/config": {"latitude": 50.0, "longitude": 10.0}}[path])
    monkeypatch.setattr(ha, "_state", lambda eid: {"state": "2.5", "attributes": {"unit_of_measurement": "kWh"}})
    assert ha.read() == {"pv_ac_forecast_today": 2.5, "pv_forecast_today": 4.2}
    assert ha.solar_planes() == (50.0, 10.0, [(30, 150, 0.87), (30, 251, 0.87)])
