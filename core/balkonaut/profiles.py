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
    # Ab hier aus dem Quellcode der Integrationen abgeleitet, nicht an Geräten bestätigt (Handbuch: Unterstützte Geräte)
    "solarman": [  # Deye u. a. über Solarman-Logger; zwei Integrationen mit derselben Domain
        # davidrapan/ha-solarman: <entry_id>_<Name>_<Plattform>, Deye-Hybrid und -Mikrowechselrichter
        (r"_pv_power_sensor$", "pv_power", False),
        (r"_total_production_sensor$", "pv_energy", False),
        (r"_battery_power_sensor$", "battery_power", True),  # Deye: positiv beim Entladen
        (r"_battery_sensor$", "battery_soc", False),
        (r"_total_battery_charge_sensor$", "battery_charge_energy", False),
        (r"_total_battery_discharge_sensor$", "battery_discharge_energy", False),
        (r"_battery_capacity_sensor$", "battery_capacity", False),
        (r"_grid_power_sensor$", "grid_power", False),
        (r"^[0-9a-z]{26}_power_sensor$", "output_power", False),  # Leistung des Wechselrichters, nicht PV oder Akku
        # StephanJoubert/home_assistant_solarman: <Name des Wechselrichters>_<Seriennummer>_<Feld>
        (r"_Total AC Output Power \(Active\)$", "pv_power", False),  # Mikrowechselrichter
        (r"_Total Production$", "pv_energy", False),
        (r"_Battery Power$", "battery_power", True),
        (r"_Battery SOC$", "battery_soc", False),
        (r"_Total Battery Charge$", "battery_charge_energy", False),
        (r"_Total Battery Discharge$", "battery_discharge_energy", False),
        (r"_Total Grid Power$", "grid_power", False),
        (r"_Total Power$", "output_power", False),
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


def direction(azimuth):
    """Himmelsrichtung zum Azimut in Grad (0 = Nord, 180 = Süd, wie Forecast.Solar in HA), z. B. „Südost 135°“."""
    names = ["Nord", "Nordost", "Ost", "Südost", "Süd", "Südwest", "West", "Nordwest"]
    return f"{names[round(azimuth / 45) % 8]} {azimuth:g}°"
