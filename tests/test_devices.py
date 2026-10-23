from pytest import approx

from balkonaut import devices
from balkonaut.devices import Devices

# Echte Antworten der Anlage des Entwicklers (23.10.2026), Kennungen ersetzt
EZHI = {"data": {"batSoc": "12.0", "batSoh": "100", "batTemp": "10.3", "devTemp": "9.2", "pvP": "51",
                 "pvTE": "985.9183", "batP": "90", "batCTE": "880.1033", "batDTE": "854.7950", "ogP": "-21",
                 "ogOTE": "112739126084637.1875", "ogITE": "286.3457", "ofgP": "39", "ofgOTE": "12.0378",
                 "ofgITE": "20498022925214.1641"}, "batS": "2", "deviceId": "D02000000000", "message": "SUCCESS"}
EM = {"id": 0, "a_act_power": 24.2, "b_act_power": 224.3, "c_act_power": 287.7, "total_act_power": 536.22}
PLUG = {"id": 0, "output": True, "apower": -6.7, "aenergy": {"total": 1612401.687}}
ANSWERS = {("10.0.0.11", "getOutputData"): EZHI, ("10.0.0.168", "rpc/EM.GetStatus?id=0"): EM,
           ("10.0.0.38", "rpc/Switch.GetStatus?id=0"): PLUG}
CONFIG = [{"type": "shelly_em", "host": "10.0.0.168"}, {"type": "apsystems_ezhi", "host": "10.0.0.11"},
          {"type": "shelly_plug", "host": "10.0.0.38"}]


def test_read(monkeypatch):
    """EZHI, Pro 3EM und Plug ergeben dieselben Messgrößen wie die Zuordnung in Home Assistant."""
    monkeypatch.setattr(devices, "_get", lambda host, path: ANSWERS[host, path])
    assert Devices(CONFIG).read() == {
        "grid_power": 536.22, "pv_power": 51, "pv_energy": 985.9183, "pv_ac_power": 39, "battery_power": 90,
        "battery_soc": 12, "battery_soh": 100, "battery_charge_energy": 880.1033,
        "battery_discharge_energy": 854.795, "output_power": 21,  # vom EZHI, nicht vom Plug
        "output_energy": approx(1612.401687)}  # vom Plug


def test_counter_glitch_and_offline(monkeypatch):
    """Zähler auf 0 (EZHI etwa alle 10 h) werden verworfen, ein Gerät ohne Antwort fehlt nur selbst."""
    answers = dict(ANSWERS)

    def get(host, path):
        if (host, path) not in answers:
            raise OSError("keine Antwort")
        return answers[host, path]
    monkeypatch.setattr(devices, "_get", get)
    adapter = Devices(CONFIG)
    adapter.read()
    answers["10.0.0.11", "getOutputData"] = {"data": {**EZHI["data"], "pvTE": "0.0000", "batCTE": "0.0000"}}
    del answers["10.0.0.38", "rpc/Switch.GetStatus?id=0"]  # Plug offline
    values = adapter.read()
    assert values["pv_energy"] is None and values["battery_charge_energy"] is None
    assert values["battery_discharge_energy"] == 854.795 and "output_energy" not in values
    answers["10.0.0.11", "getOutputData"] = EZHI
    assert adapter.read()["pv_energy"] == 985.9183


def test_invert(monkeypatch):
    """Plug allein (ohne Speicher), am Einspeisepunkt mit umgekehrtem Vorzeichen angeschlossen."""
    monkeypatch.setattr(devices, "_get", lambda host, path: ANSWERS[host, path])
    plug = Devices([{"type": "shelly_plug", "host": "10.0.0.38", "invert": ["output_power"]}])
    assert plug.read()["output_power"] == 6.7


def test_config_adapter():
    """config.yaml mit devices nimmt die Geräte direkt, sonst Home Assistant, ohne beides keinen Adapter."""
    from app.config import adapter
    from balkonaut.homeassistant import HomeAssistant
    assert isinstance(adapter({"devices": CONFIG}), Devices)
    assert isinstance(adapter({"home_assistant": {"url": "http://ha", "token": "t", "entities": {}}}), HomeAssistant)
    assert adapter({}) is None


def test_forecast_and_planes(monkeypatch):
    """Prognose je Wechselrichter aus den Flächen, höchstens einmal je Stunde; Flächen für den Jahresverlauf."""
    calls = []

    def today(lat, lon, tilt, azimuth, kwp):
        calls.append(azimuth)
        return {150: 4.2, 251: 3.1}[azimuth]
    monkeypatch.setattr(devices, "_get", lambda host, path: ANSWERS[host, path])
    monkeypatch.setattr(devices.forecast, "today", today)
    planes = [{"declination": 30, "azimuth": 150, "kwp": 0.87, "inverter": "storage"},
              {"declination": 30, "azimuth": 251, "kwp": 0.87, "inverter": "extra"}]
    adapter = Devices(CONFIG, {"lat": 50.0, "lon": 10.0}, planes)
    values = adapter.read()
    assert values["pv_forecast_today"] == 4.2 and values["pv_ac_forecast_today"] == 3.1
    adapter.read()
    assert calls == [150, 251]  # zweiter Abruf erst nach einer Stunde
    assert adapter.solar_planes() == (50.0, 10.0, [(30, 150, 0.87), (30, 251, 0.87)])
    assert Devices(CONFIG).solar_planes() == (0.0, 0.0, [])
