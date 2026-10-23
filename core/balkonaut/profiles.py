"""Geräteprofile: aus den Entitäten eines Geräts die Messgrößen ableiten, für die geführte Einrichtung.

Eine Entität ist ein dict mit entity_id, platform, unique_id, device_class, unit_of_measurement und state_class.
Erst gelten die Profile bekannter Integrationen (Endung der unique_id, stabil auch nach Umbenennen),
danach Gerätedaten wie device_class und Einheit, aber nur, wenn die Zuordnung eindeutig ist.
"""
import re

# Victron GX über MQTT, Bibliothek victron-mqtt: <Anlage>_<Gerät>_<Messwert>; Akku positiv beim Laden (dokumentiert)
VICTRON_MQTT = [
    (r"_system_dc_pv_power$", "pv_power", False),
    (r"_system_dc_pv_energy$", "pv_energy", False),
    (r"_system_dc_battery_power$", "battery_power", False),
    (r"_system_dc_battery_soc$", "battery_soc", False),
    (r"_system_dc_battery_charge_energy$", "battery_charge_energy", False),
    (r"_system_dc_battery_discharge_energy$", "battery_discharge_energy", False),
    (r"_grid_power$", "grid_power", False),  # Netzzähler, Summe aller Phasen
]

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
    "huawei_solar": [  # wlcrs/huawei_solar: <Seriennummer>_<Registername>, SUN2000 mit LUNA2000 und Power Meter
        (r"_input_power$", "pv_power", False),  # Gesamtertrag zählt Akku-Entladung mit, daher kein pv_energy
        (r"(?<!meter)_active_power$", "output_power", False),
        (r"_power_meter_active_power$", "grid_power", True),  # Huawei: positiv bei Einspeisung (Wiki)
        (r"_storage_charge_discharge_power$", "battery_power", False),
        (r"_storage_state_of_capacity$", "battery_soc", False),
        (r"_storage_total_charge$", "battery_charge_energy", False),
        (r"_storage_total_discharge$", "battery_discharge_energy", False),
        (r"_storage_rated_capacity$", "battery_capacity", False),
        (r"_storage_discharging_cutoff_capacity$", "battery_soc_min", False),
        (r"_storage_charging_cutoff_capacity$", "battery_soc_max", False),
    ],
    "mqtt": [  # Hoymiles über MQTT-Discovery, unique_id aus der Firmware
        (r"^[0-9a-fA-F]{12}_ch0_Power$", "pv_power", False),  # OpenDTU: <Seriennummer>_ch0_<Feld>, AC-Leistung
        (r"_ch0_P_AC$", "pv_power", False),  # AhoyDTU: je Wechselrichter <Seriennummer hex>_ch0_<Feld>
        (r"_ch0_YieldTotal$", "pv_energy", False),  # beide
        (r"_TOTAL_total_P_AC$", "pv_power", False),  # AhoyDTU: Summe aller Wechselrichter
        (r"_TOTAL_total_YieldTotal$", "pv_energy", False),
    ],
    "anker_solix": [  # thomluther/ha-anker-solix: <Seriennummer oder Anlage>_<Schlüssel>, klein geschrieben
        (r"_input_power$", "pv_power", False),  # Solarbank: PV-Leistung des Geräts
        (r"_solar_power_total$", "pv_power", False),
        (r"_battery_power_signed$", "battery_power", False),  # README: positiv beim Laden
        (r"_state_of_charge$", "battery_soc", False),
        (r"_ac_to_home_load$", "output_power", False),
        (r"_grid_power_signed$", "grid_power", False),  # Vorzeichen nicht dokumentiert
        # Energie nur als Tageswerte aus der Cloud-Statistik, daher keine Zähler; Balkonaut summiert selbst
    ],
    "zendure_ha": [  # Zendure/Zendure-HA: <Gerätename>_<Eigenschaft> in snake_case, SolarFlow, Hyper, AIO
        (r"_solar_input_power$", "pv_power", False),
        (r"_aggr_solar$", "pv_energy", False),
        (r"_bat_in_out$", "battery_power", True),  # Entladen minus Laden
        (r"_electric_level$", "battery_soc", False),
        (r"_aggr_charge$", "battery_charge_energy", False),
        (r"_aggr_discharge$", "battery_discharge_energy", False),
        (r"_total_kwh$", "battery_capacity", False),
        (r"_min_soc$", "battery_soc_min", False),
        (r"_soc_set$", "battery_soc_max", False),
        (r"_output_home_power$", "output_power", False),
        (r"_aggr_output_home$", "output_energy", False),
        (r"_output_limit$", "output_power_limit", False),
    ],
    "ecoflow_cloud": [  # tolwi/hassio-ecoflow-cloud: ecoflow-[api-]<Seriennummer>-<Schlüssel mit - statt . und _>
        # PowerStream; Vorzeichen der Akkuleistung nicht dokumentiert
        (r"-20-1-batSoc$", "battery_soc", False),
        (r"-20-1-batInputWatts$", "battery_power", False),
        (r"-20-1-invOutputWatts$", "output_power", False),
        (r"-20-1-lowerLimit$", "battery_soc_min", False),
        (r"-20-1-upperLimit$", "battery_soc_max", False),
        # STREAM; Vorzeichen von Akku und Netz nicht dokumentiert
        (r"-powGetPvSum$", "pv_power", False),
        (r"-f32ShowSoc$", "battery_soc", False),
        (r"-powGetBpCms$", "battery_power", False),
        (r"-accuChgEnergy$", "battery_charge_energy", False),
        (r"-accuDsgEnergy$", "battery_discharge_energy", False),
        (r"-cmsMinDsgSoc$", "battery_soc_min", False),
        (r"-cmsMaxChgSoc$", "battery_soc_max", False),
        (r"-gridConnectionPower$", "output_power", False),
        (r"-powGetSysGrid$", "grid_power", False),
        (r"-watts$", "output_power", False),  # Smart Plug am Einspeisepunkt
    ],
    "growatt_server": [  # Growatt in Home Assistant: <Seriennummer>-<Schlüssel>; Akku und Netz nur getrennt je
        # Richtung, daher ohne Akkuleistung und Netz. NOAH wird von der Integration nicht unterstützt.
        (r"-(inverter|tlx)_internal_wattage$|-mix_wattage_pv_all$|-storage_solar_production$", "pv_power", False),
        (r"-(inverter|tlx)_current_wattage$", "output_power", False),
        (r"-tlx_solar_generation_total$|-(mix_solar_generation|storage_solar_output)_lifetime$|-inverter_energy_total$",
         "pv_energy", False),
        (r"-(tlx|mix)_statement_of_charge$|-storage_battery_percentage$", "battery_soc", False),
        (r"-tlx_all_batteries_charge_total$|-mix_battery_charge_lifetime$", "battery_charge_energy", False),
        (r"-tlx_all_batteries_discharge_total$|-mix_battery_discharge_lifetime$", "battery_discharge_energy", False),
    ],
    "victron_gx": VICTRON_MQTT,  # in Home Assistant
    "victron_mqtt": VICTRON_MQTT,  # tomer-w/ha-victron-mqtt
    "victron": [  # sfstar/hass-victron (Modbus): <Slave-ID>_<Register>; Netz nur je Phase
        (r"_system_battery_power$", "battery_power", False),
        (r"_system_battery_soc$", "battery_soc", False),
    ],
    "foxess_modbus": [  # nathanmarlor/foxess_modbus: foxess_modbus_[Präfix_]<Schlüssel>; Akku nur getrennt je Richtung
        (r"_pv_power_now$", "pv_power", False),
        (r"_solar_energy_total$", "pv_energy", False),
        (r"_rpower$", "output_power", False),
        (r"_grid_ct$", "grid_power", True),  # positiv bei Einspeisung (Feed-in = Grid CT > 0)
        (r"_battery_soc$", "battery_soc", False),
        (r"_battery_soh$", "battery_soh", False),
        (r"_battery_charge_total$", "battery_charge_energy", False),
        (r"_battery_discharge_total$", "battery_discharge_energy", False),
        (r"_min_soc$", "battery_soc_min", False),
        (r"_max_soc$", "battery_soc_max", False),
    ],
    "foxess": [  # macxq/foxess-ha (Cloud): <Geräte-ID><Kennung> ohne Trennzeichen; Energie nur als Berichtswerte
        (r"pv-power$", "pv_power", False),
        (r"inv-Bat-Power$", "battery_power", False),  # Vorzeichen nicht dokumentiert
        (r"bat-soc$", "battery_soc", False),
        (r"bat-soh$", "battery_soh", False),
    ],
    "hoymiles_wifi": [  # suaveolent/ha-hoymiles-wifi: hoymiles_<entry_id>_<Schlüssel>, HMS-xxxW-2T und DTUs
        (r"_dtu_power$", "pv_power", False),  # kein Gesamtzähler, Balkonaut summiert die Leistung selbst
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
