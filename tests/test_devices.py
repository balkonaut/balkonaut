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
ANSWERS = {("10.0.0.11", "getOutputData"): EZHI, ("10.0.0.11", "getDeviceInfo"): {"data": {"type": "EZHI", "batteryCapacity": "5.52"}},
           ("10.0.0.168", "rpc/EM.GetStatus?id=0"): EM,
           ("10.0.0.38", "rpc/Switch.GetStatus?id=0"): PLUG}
CONFIG = [{"type": "shelly_em", "host": "10.0.0.168"}, {"type": "apsystems_ezhi", "host": "10.0.0.11"},
          {"type": "shelly_plug", "host": "10.0.0.38"}]


def test_read(monkeypatch):
    """EZHI, Pro 3EM und Plug ergeben dieselben Messgrößen wie die Zuordnung in Home Assistant."""
    monkeypatch.setattr(devices, "_get", lambda host, path: ANSWERS[host, path])
    assert Devices(CONFIG).read() == {
        "grid_power": 536.22, "pv_power": 51, "pv_energy": 985.9183, "pv_ac_power": 39, "battery_power": 90,
        "battery_soc": 12, "battery_soh": 100, "battery_capacity": 5.52, "battery_charge_energy": 880.1033,
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

    def estimate(lat, lon, tilt, azimuth, kwp):
        calls.append(azimuth)
        return {150: 4.2, 251: 3.1}[azimuth], {3600.0: {150: 0.5, 251: 0.25}[azimuth]}
    monkeypatch.setattr(devices, "_get", lambda host, path: ANSWERS[host, path])
    monkeypatch.setattr(devices.forecast, "estimate", estimate)
    planes = [{"declination": 30, "azimuth": 150, "kwp": 0.87, "inverter": "storage"},
              {"declination": 30, "azimuth": 251, "kwp": 0.87, "inverter": "extra"}]
    adapter = Devices(CONFIG, {"lat": 50.0, "lon": 10.0}, planes)
    values = adapter.read()
    assert values["pv_forecast_today"] == 4.2 and values["pv_ac_forecast_today"] == 3.1
    adapter.read()
    assert calls == [150, 251]  # zweiter Abruf erst zur nächsten halben Stunde
    assert adapter.forecast.current_hours() == {3600.0: 0.75}  # Stundenwerte aller Flächen zusammen
    assert adapter.solar_planes() == (50.0, 10.0, [(30, 150, 0.87), (30, 251, 0.87)])
    assert Devices(CONFIG).solar_planes() == (0.0, 0.0, [])


def test_forecast_retry(monkeypatch):
    """Fehlgeschlagener Abruf: keine Prognose, nächster Versuch erst zur nächsten halben Stunde, nicht bei jeder Messung."""
    import time
    calls = []

    def estimate(*args):
        calls.append(args)
        raise OSError("nicht erreichbar")
    monkeypatch.setattr(devices.forecast, "estimate", estimate)
    planes = devices.forecast.Planes({"lat": 50.0, "lon": 10.0}, [{"declination": 30, "azimuth": 150, "kwp": 0.87}])
    assert planes.read() == {} and planes.read() == {} and len(calls) == 1
    assert 0 < planes.next - time.time() <= 1800 and planes.next % 1800 == 0


def test_detect(monkeypatch):
    """Erkennung an der Antwort; HTTP-Fehler heißt nächste Probe, ohne Webserver geht es mit Victron weiter."""
    import urllib.error
    answers = {("pro3em", "shelly"): {"app": "Pro3EM"}, ("pro3em", "rpc/EM.GetStatus?id=0"): EM,
               ("plug", "shelly"): {"app": "OutdoorPlugSG3"},
               ("proem", "shelly"): {"app": "ProEM"}, ("proem", "rpc/EM1.GetStatus?id=0"): {"id": 0, "act_power": 120.5},
               ("ezhi", "getDeviceInfo"): {"data": {"type": "EZHI"}},
               ("opendtu", "api/livedata/status"): {"inverters": [], "total": {}, "hints": {}},
               ("ahoy", "api/generic"): {"version": "0.8.155", "modules": "MDH", "esp_type": "ESP32"}}

    def get(host, path):
        if host == "weg":
            raise urllib.error.URLError("timed out")
        if (host, path) not in answers:
            raise urllib.error.HTTPError(path, 404, "Not Found", {}, None)
        return answers[host, path]
    monkeypatch.setattr(devices, "_get", get)
    monkeypatch.setattr(devices, "_connect", lambda *a, **k: (_ for _ in ()).throw(ConnectionRefusedError()))  # kein Victron
    found = {h: devices.detect(h) for h in ("pro3em", "plug", "proem", "ezhi", "opendtu", "ahoy")}
    assert found == {"pro3em": "shelly_em", "plug": "shelly_plug", "proem": "shelly_em1", "ezhi": "apsystems_ezhi",
                     "opendtu": "opendtu", "ahoy": "ahoydtu"}
    for host in ("weg", "unbekannt"):
        try:
            devices.detect(host)
            raise AssertionError(host)
        except ValueError:
            pass


def test_dtu(monkeypatch):
    """OpenDTU mit Zähler, AhoyDTU nur Leistung; ohne Speicher Erzeugung und Abgabe; der Plug gilt vor der DTU."""
    opendtu = {"inverters": [], "total": {"Power": {"v": 412.3, "u": "W", "d": 1}, "YieldTotal": {"v": 1234.567, "u": "kWh", "d": 3}}}
    ahoy = {"inverter": [{"id": 0, "cur_pwr": 200.0}, {"id": 1, "cur_pwr": 150.5}]}
    answers = {("dtu", "api/livedata/status"): opendtu, ("ahoy", "api/index"): ahoy, **ANSWERS}
    monkeypatch.setattr(devices, "_get", lambda host, path: answers[host, path])
    assert Devices([{"type": "opendtu", "host": "dtu"}]).read() == {
        "pv_power": 412.3, "pv_energy": 1234.567, "output_power": 412.3, "output_energy": 1234.567}
    assert Devices([{"type": "ahoydtu", "host": "ahoy"}]).read() == {"pv_power": 350.5, "output_power": 350.5}
    both = Devices([{"type": "shelly_plug", "host": "10.0.0.38"}, {"type": "opendtu", "host": "dtu"}]).read()
    assert both["output_power"] == -6.7 and both["pv_power"] == 412.3


def test_estimate(monkeypatch):
    """Forecast.Solar /estimate: Tageswert von heute, Stundenwerte von heute dem Stundenbeginn zugeordnet."""
    import io
    import json
    from datetime import datetime
    from balkonaut.analytics import TZ
    body = {"result": {"watt_hours_day": {"2026-10-25": 2250, "2026-10-26": 3000},
                       "watt_hours_period": {"2026-10-25 07:29:00": 0, "2026-10-25 08:00:00": 40, "2026-10-25 09:00:00": 210,
                                             "2026-10-25 16:46:00": 35, "2026-10-26 09:00:00": 300}}}

    class Answer(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    urls = []
    monkeypatch.setattr(devices.forecast.urllib.request, "urlopen",
                        lambda url, timeout: urls.append(url) or Answer(json.dumps(body).encode()))
    day, hours = devices.forecast.estimate(52.0, 11.3, 30, 150, 0.87)
    at = lambda h: datetime(2026, 10, 25, h, tzinfo=TZ).timestamp()
    assert day == 2.25 and urls == ["https://api.forecast.solar/estimate/52.0/11.3/30/-30/0.87"]
    assert hours == {at(7): 0.04, at(8): 0.21, at(16): 0.035}


def test_victron(monkeypatch):
    """Victron GX über Modbus TCP und MQTT: gleiche Messgrößen, Netz über alle Phasen, AC-gekoppelte PV getrennt.
    Fake-Gerät mit Antworten wie tools/victron-mock (Register laut Liste 3.81, Nachrichten wie dbus-flashmq)."""
    import json
    import struct
    devices._portal_id.cache_clear()
    regs = {842: -368, 843: 50, 850: 120, 811: 40, 817: 700, 818: 80, 819: 33, 820: 300, 821: -20, 822: 5}
    msgs = {"/Dc/Battery/Power": -368, "/Dc/Battery/Soc": 50, "/Dc/Pv/Power": 120, "/Ac/PvOnGrid/L1/Power": 40,
            "/Ac/Consumption/L1/Power": 700, "/Ac/Consumption/L2/Power": 80, "/Ac/Consumption/L3/Power": 33,
            "/Ac/Grid/L1/Power": 300, "/Ac/Grid/L2/Power": -20, "/Ac/Grid/L3/Power": 5, "/Ac/Genset/L1/Power": None,
            "/Serial": "x" * 200}  # lange Nachricht: Restlänge über zwei Bytes

    def pub(topic, payload):
        return devices._packet(0x30, devices._str(topic) + payload)

    class GX:
        def __init__(self, port):
            self.port, self.out = port, b""

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def recv(self, n):
            chunk, self.out = self.out[:n], self.out[n:]
            return chunk

        def sendall(self, data):
            if self.port == 502:
                tid, _, _, unit, _, start, count = struct.unpack(">HHHBBHH", data)
                body = bytes([3, 2 * count]) + b"".join(struct.pack(">h", regs.get(a, 0)) for a in range(start, start + count))
                self.out += struct.pack(">HHHB", tid, 0, len(body) + 1, unit) + body
            elif data[0] == 0x82:  # SUBSCRIBE: SUBACK, bei der Suche gleich die Serial-Meldung
                self.out += b"\x90\x03\x00\x01\x00" + (pub("N/c0619a/system/0/Serial", b'{"value": "c0619a"}')
                                                       if b"N/+/" in data else b"")
            elif data[0] == 0x30:  # Keepalive: alles, ein verschwundenes Gerät leer, dann Abschluss
                self.out += b"".join(pub(f"N/c0619a/system/0{p}", json.dumps({"value": v}).encode()) for p, v in msgs.items())
                self.out += pub("N/c0619a/solarcharger/278/Yield/Power", b'{"value": 80}')
                self.out += pub("N/c0619a/solarcharger/278/CustomName", b'{"value": "MPPT Ost"}')
                self.out += pub("N/c0619a/solarcharger/279/Yield/Power", b'{"value": 40}')
                self.out += pub("N/c0619a/solarcharger/279/ProductName", b'{"value": "SmartSolar MPPT 75/15"}')
                self.out += pub("N/c0619a/vebus/276/Ac/Out/L1/P", b"") + pub("N/c0619a/full_publish_completed", b'{"value": 1}')

    monkeypatch.setattr(devices, "_connect", lambda host, port, timeout=5: GX(port))
    expected = {"pv_power": 120, "pv_ac_power": 40, "battery_power": -368, "battery_soc": 50, "grid_power": 285,
                "output_power": 528}  # Verbrauch 813 W minus Netzbezug 285 W
    assert devices.victron_modbus("gx") == expected
    assert devices.victron_mqtt("gx") == expected | {"pv_mppt_278_power": 80, "pv_mppt_279_power": 40}  # je Laderegler
    assert devices.LABELS["pv_mppt_278_power"] == "MPPT Ost" and devices.LABELS["pv_mppt_279_power"] == "SmartSolar MPPT 75/15"
    assert devices._portal_id("gx") == "c0619a"
