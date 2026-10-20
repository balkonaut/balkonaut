"""Home-Assistant-Adapter: liest Entitäten über die REST-API und normalisiert Einheiten und Vorzeichen.

Neutrale Messgrößen (Leistung in W, Energie in kWh):
    grid_power      Netz, + Bezug / - Einspeisung (über alle Phasen saldiert)
    pv_power        PV-Erzeugung am Speicher-Wechselrichter
    pv_ac_power     AC-gekoppelte Erzeugung, z. B. Mikrowechselrichter am Off-Grid-Port
    battery_power   Akku, + Laden / - Entladen
    battery_soc     Ladestand in %
    output_power    Abgabe des Speichersystems ins Hausnetz, + Abgabe
    output_energy   Zähler Abgabe ins Hausnetz, am Einspeisepunkt gemessen
    pv_energy       Zähler PV-Erzeugung am Speicher-Wechselrichter
    battery_charge_energy, battery_discharge_energy   Zähler Akku

Welche Quelle für welche Größe maßgeblich ist: docs/messquellen.md
"""
import json
import logging
from datetime import datetime, timezone
import urllib.error
import urllib.request

# Umrechnung auf W bzw. kWh
UNITS = {"kW": 1000.0, "Wh": 0.001}

log = logging.getLogger(__name__)


class HomeAssistant:
    def __init__(self, url, token, entities):
        """entities: {Messgröße: (entity_id, faktor)}; faktor -1 dreht das Vorzeichen."""
        self.url = url.rstrip("/")
        self.token = token
        self.entities = entities

    def _get(self, path, timeout=10):
        req = urllib.request.Request(self.url + path, headers={"Authorization": "Bearer " + self.token})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def _state(self, entity_id):
        try:
            return self._get(f"/api/states/{entity_id}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def read(self):
        """Aktuelle Werte aller Messgrößen; None bei unbekannter oder nicht verfügbarer Entität."""
        values = {}
        for key, (eid, factor) in self.entities.items():
            try:
                values[key] = normalize(self._state(eid), factor)
            except OSError as e:  # HA nicht erreichbar oder Zeitüberschreitung
                log.warning("%s nicht lesbar: %s", eid, e)
                values[key] = None
        return values

    def history(self, start, end):
        """Verlauf aller Messgrößen aus dem HA-Recorder: {Messgröße: [(ts, wert), ...]}, tageweise abgefragt."""
        by_id = {eid: (key, factor) for key, (eid, factor) in self.entities.items()}
        units = {eid: ((self._state(eid) or {}).get("attributes") or {}).get("unit_of_measurement") for eid in by_id}
        out = {key: [] for key in self.entities}
        for t in range(int(start), int(end), 86400):
            query = (f"/api/history/period/{iso(t)}?end_time={iso(min(t + 86400, end))}"
                     f"&filter_entity_id={','.join(by_id)}&minimal_response&no_attributes")
            for series in self._get(query, timeout=120):
                eid = series[0]["entity_id"]
                key, factor = by_id[eid]
                attrs = {"unit_of_measurement": units[eid]}
                out[key] += [(datetime.fromisoformat(p["last_changed"]).timestamp(),
                              normalize({"state": p["state"], "attributes": attrs}, factor)) for p in series]
        return {key: sorted(points) for key, points in out.items()}

    def solar_planes(self):
        """Standort und Flächen aus der Forecast.Solar-Integration: (lat, lon, [(neigung, azimut, kwp)])."""
        planes = []
        for entry in self._get("/api/config/config_entries/entry?domain=forecast_solar"):
            diag = self._get(f"/api/diagnostics/config_entry/{entry['entry_id']}")
            for sub in diag["data"]["entry"].get("subentries") or []:
                d = sub["data"]
                planes.append((d["declination"], d["azimuth"], d["modules_power"] / 1000))
        cfg = self._get("/api/config")
        return cfg["latitude"], cfg["longitude"], sorted(planes)


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize(state, factor=1):
    if state is None:
        return None
    try:
        value = float(state["state"])
    except ValueError:  # unavailable, unknown
        return None
    return value * UNITS.get(state["attributes"].get("unit_of_measurement"), 1.0) * factor
