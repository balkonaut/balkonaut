"""Geräteprofile: aus den Entitäten eines Geräts die Messgrößen ableiten, für die geführte Einrichtung.

Eine Entität ist ein dict mit entity_id, platform, unique_id, device_class, unit_of_measurement und state_class.
Erst gelten die Profile bekannter Integrationen (Endung der unique_id, stabil auch nach Umbenennen),
danach Gerätedaten wie device_class und Einheit, aber nur, wenn die Zuordnung eindeutig ist.
"""
import re

# Integration -> [(Muster für die unique_id, Messgröße, Vorzeichen drehen)], nur an echten Geräten geprüft
PROFILES = {
    "apsystems_ezhi_local": [  # APsystems EZHI, HACS-Integration „APsystems EZHI Local API“
        (r"_photovoltaic_power$", "pv_power", False),
        (r"_photovoltaic_energy$", "pv_energy", False),
        (r"_battery_power$", "battery_power", False),
        (r"_battery_soc$", "battery_soc", False),
        (r"_battery_soh$", "battery_soh", False),
        (r"_battery_charge_energy$", "battery_charge_energy", False),
        (r"_battery_discharge_energy$", "battery_discharge_energy", False),
        (r"_battery_capacity$", "battery_capacity", False),
        (r"_ongrid_power$", "output_power", True),  # negativ bei Abgabe ins Haus
        (r"_ongrid_output_energy$", "output_energy", False),
        (r"_offgrid_power$", "pv_ac_power", False),  # Off-Grid-Port, z. B. ein EZ1-M als Zusatz
        (r"_cloud_power_limit_state$", "output_power_limit", False),
        (r"_cloud_socmin$", "battery_soc_min", False),
        (r"_cloud_socmax$", "battery_soc_max", False),
        (r"_cloud_discharge_protection$", "battery_discharge_protection", False),
    ],
    "apsystems": [  # APsystems EZ1-M, Integration in Home Assistant
        (r"_total_power$", "pv_power", False),
        (r"_lifetime_production$", "pv_energy", False),
        (r"_output_limit$", "output_power_limit", False),
    ],
    "shelly": [
        (r"-em:\d+-total_act_power$", "grid_power", False),  # Pro 3EM, über alle Phasen saldiert
        (r"-switch:\d+-power$", "output_power", False),  # Plug am Einspeisepunkt, Vorzeichen je nach Anschluss
        (r"-switch:\d+-energy$", "output_energy", False),
    ],
    "forecast_solar": [
        (r"_energy_production_today$", "pv_forecast_today", False),
    ],
}

POWER = ("power", frozenset({"W", "kW"}), None)
ENERGY = ("energy", frozenset({"Wh", "kWh"}), frozenset({"total", "total_increasing"}))
PERCENT = ("battery", frozenset({"%"}), None)
# Messgröße -> (device_class, Einheiten, state_class) für Geräte ohne Profil
RULES = {
    "grid_power": POWER, "pv_power": POWER, "pv_ac_power": POWER, "battery_power": POWER, "output_power": POWER,
    "output_power_limit": POWER,
    "output_energy": ENERGY, "pv_energy": ENERGY, "battery_charge_energy": ENERGY,
    "battery_discharge_energy": ENERGY,
    "battery_soc": PERCENT, "battery_soc_min": PERCENT, "battery_soc_max": PERCENT,
    "battery_discharge_protection": PERCENT,
    "battery_capacity": ("energy_storage", frozenset({"Wh", "kWh"}), None),
}


def suggest(entities, keys):
    """Vorschlag {Messgröße: entity_id} und Liste der Messgrößen mit gedrehtem Vorzeichen, nur für keys."""
    found, invert = {}, []
    for e in entities:
        for pattern, key, flip in PROFILES.get(e.get("platform"), []):
            if key in keys and key not in found and re.search(pattern, e.get("unique_id") or ""):
                found[key] = e["entity_id"]
                if flip:
                    invert.append(key)
    used = set(found.values())
    for rule in {RULES[k] for k in keys if k in RULES}:
        open_keys = [k for k in keys if RULES.get(k) == rule and k not in found]
        candidates = [e["entity_id"] for e in entities if e["entity_id"] not in used and matches(e, rule)]
        if len(open_keys) == 1 and len(candidates) == 1:  # mehrdeutig: lieber leer lassen als falsch raten
            found[open_keys[0]] = candidates[0]
    return found, invert


def matches(entity, rule):
    device_class, units, state_classes = rule
    return (entity.get("device_class") == device_class and entity.get("unit_of_measurement") in units
            and (state_classes is None or entity.get("state_class") in state_classes))
