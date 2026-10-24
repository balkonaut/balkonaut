"""Direkte Geräte-Adapter: liest Geräte im Heimnetz ohne Home Assistant, lokal per HTTP ohne Anmeldung.

Liefert dieselben Messgrößen wie der Home-Assistant-Adapter (W, kWh, Vorzeichen siehe dort).
Geprüft an APsystems EZHI, Shelly Pro 3EM und Shelly Outdoor Plug S Gen3 (Oktober 2026).
"""
import json
import logging
import urllib.request

from . import forecast

log = logging.getLogger(__name__)


def _get(host, path, timeout=5):
    with urllib.request.urlopen(f"http://{host}/{path}", timeout=timeout) as r:
        return json.load(r)


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def apsystems_ezhi(host):
    """APsystems EZHI, lokale API (in der APsystems-App den lokalen Modus aktivieren)."""
    d = _get(host, "getOutputData").get("data") or {}
    og = _num(d.get("ogP"))
    return {
        "pv_power": _num(d.get("pvP")),
        "pv_energy": _num(d.get("pvTE")),
        "pv_ac_power": _num(d.get("ofgP")),  # Off-Grid-Port, z. B. ein EZ1-M
        "battery_power": _num(d.get("batP")),  # + Laden
        "battery_soc": _num(d.get("batSoc")),
        "battery_soh": _num(d.get("batSoh")),
        "battery_charge_energy": _num(d.get("batCTE")),
        "battery_discharge_energy": _num(d.get("batDTE")),
        "output_power": None if og is None else 0.0 - og,  # EZHI: negativ bei Abgabe ins Haus; 0.0 - og ohne -0,0
        # ogOTE und ofgITE liefert die Firmware unsinnig (z. B. 1,1e14), daher nicht verwendet
    }


def shelly_em(host):
    """Shelly Pro 3EM: Netzleistung über alle Phasen saldiert, + Bezug."""
    return {"grid_power": _num(_get(host, "rpc/EM.GetStatus?id=0").get("total_act_power"))}


def shelly_plug(host):
    """Shelly Plug (Gen2, Gen3) am Einspeisepunkt: Abgabe ins Haus mit Zähler."""
    s = _get(host, "rpc/Switch.GetStatus?id=0")
    wh = _num((s.get("aenergy") or {}).get("total"))
    return {"output_power": _num(s.get("apower")), "output_energy": None if wh is None else wh / 1000}


# Reihenfolge: spätere Geräte überschreiben frühere, so gilt die Abgabe-Leistung des Speichers vor der des Plugs
# und der Zähler am Einspeisepunkt, den der Speicher nicht liefert, bleibt (Handbuch, Messquellen)
TYPES = {"shelly_plug": shelly_plug, "apsystems_ezhi": apsystems_ezhi, "shelly_em": shelly_em}


def detect(host):
    """Gerätetyp unter host erkennen (Shelly über /shelly, EZHI über /getDeviceInfo); ValueError, wenn unbekannt."""
    try:
        app = _get(host, "shelly").get("app") or ""
        if app.startswith("Pro3EM"):
            return "shelly_em"
        if "Plug" in app:  # z. B. PlusPlugS, PlugSG3, OutdoorPlugSG3
            return "shelly_plug"
    except (OSError, ValueError):
        pass
    try:
        if (_get(host, "getDeviceInfo").get("data") or {}).get("type") == "EZHI":
            return "apsystems_ezhi"
    except (OSError, ValueError):
        pass
    raise ValueError(f"Unter {host} antwortet kein bekanntes Gerät")


class Devices:
    def __init__(self, devices, location=None, planes=()):
        """devices: [{"type": ..., "host": ..., "invert": [Messgrößen]}], location: {"lat": ..., "lon": ...},
        planes: [{"declination": ..., "azimuth": ..., "kwp": ..., "inverter": "storage" | "extra"}]"""
        self.devices = sorted(devices, key=lambda d: list(TYPES).index(d["type"]))
        self.forecast = forecast.Planes(location, planes)
        self.high = {}  # höchster Zählerstand je Messgröße

    def read(self):
        """Aktuelle Werte aller Geräte; fehlt ein Gerät, fehlen nur seine Messgrößen."""
        values = {}
        for dev in self.devices:
            try:
                new = TYPES[dev["type"]](dev["host"])
            except (OSError, ValueError) as e:  # nicht erreichbar, Zeitüberschreitung, kein JSON
                log.warning("%s nicht lesbar: %s", dev["host"], e)
                continue
            for key in dev.get("invert", []):
                if new.get(key) is not None:
                    new[key] = -new[key]
            values.update(new)
        values.update(self.forecast.read())
        for key, value in values.items():
            if key.endswith("_energy") and value is not None:
                # Zähler fallen nie: der EZHI meldet etwa alle 10 h eine Minute lang alle Zähler als 0
                if value <= 0 or value < 0.9 * self.high.get(key, 0):
                    values[key] = None
                else:
                    self.high[key] = max(value, self.high.get(key, 0))
        return values

    def solar_planes(self):
        """Standort und Flächen aus der Konfiguration, für den Jahresverlauf (PVGIS)."""
        return self.forecast.solar_planes()
