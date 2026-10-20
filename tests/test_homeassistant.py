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
