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

    def _state(self, entity_id):
        req = urllib.request.Request(f"{self.url}/api/states/{entity_id}",
                                     headers={"Authorization": "Bearer " + self.token})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.load(r)
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


def normalize(state, factor=1):
    if state is None:
        return None
    try:
        value = float(state["state"])
    except ValueError:  # unavailable, unknown
        return None
    return value * UNITS.get(state["attributes"].get("unit_of_measurement"), 1.0) * factor
