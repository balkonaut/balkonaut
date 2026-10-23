from balkonaut.profiles import direction, suggest


def e(entity_id, platform, unique_id, device_class=None, unit=None, state_class=None):
    return {"entity_id": entity_id, "platform": platform, "unique_id": unique_id, "device_class": device_class,
            "unit_of_measurement": unit, "state_class": state_class}


# Echte Registry-Daten der Anlage des Entwicklers (Oktober 2026), MAC-Adressen und Kennungen ersetzt
EZHI = [
    e("sensor.apsystens_ezhi_battery_status", "apsystems_ezhi_local", "apsystems_APSystens EZHI_battery_status"),
    e("sensor.apsystens_ezhi_photovoltaic_power", "apsystems_ezhi_local", "apsystems_APSystens EZHI_photovoltaic_power", "power", "W", "measurement"),
    e("sensor.apsystens_ezhi_photovoltaic_energy", "apsystems_ezhi_local", "apsystems_APSystens EZHI_photovoltaic_energy", "energy", "kWh", "total"),
    e("sensor.apsystens_ezhi_battery_power", "apsystems_ezhi_local", "apsystems_APSystens EZHI_battery_power", "power", "W", "measurement"),
    e("sensor.apsystens_ezhi_battery_state_of_charge", "apsystems_ezhi_local", "apsystems_APSystens EZHI_battery_soc", "battery", "%", "measurement"),
    e("sensor.apsystens_ezhi_battery_state_of_health", "apsystems_ezhi_local", "apsystems_APSystens EZHI_battery_soh", None, "%", "measurement"),
    e("sensor.apsystens_ezhi_battery_temperature", "apsystems_ezhi_local", "apsystems_APSystens EZHI_battery_temperature", "temperature", "°C", "measurement"),
    e("sensor.apsystens_ezhi_battery_total_charge_energy", "apsystems_ezhi_local", "apsystems_APSystens EZHI_battery_charge_energy", "energy", "kWh", "total"),
    e("sensor.apsystens_ezhi_battery_total_discharge_energy", "apsystems_ezhi_local", "apsystems_APSystens EZHI_battery_discharge_energy", "energy", "kWh", "total"),
    e("sensor.apsystens_ezhi_battery_capacity", "apsystems_ezhi_local", "apsystems_APSystens EZHI_battery_capacity", "energy_storage", "kWh", "measurement"),
    e("sensor.apsystens_ezhi_on_grid_power", "apsystems_ezhi_local", "apsystems_APSystens EZHI_ongrid_power", "power", "W", "measurement"),
    e("sensor.apsystens_ezhi_on_grid_output_energy", "apsystems_ezhi_local", "apsystems_APSystens EZHI_ongrid_output_energy", "energy", "kWh", "total"),
    e("sensor.apsystens_ezhi_on_grid_input_energy", "apsystems_ezhi_local", "apsystems_APSystens EZHI_ongrid_input_energy", "energy", "kWh", "total"),
    e("sensor.apsystens_ezhi_off_grid_power", "apsystems_ezhi_local", "apsystems_APSystens EZHI_offgrid_power", "power", "W", "measurement"),
    e("sensor.apsystens_ezhi_off_grid_output_energy", "apsystems_ezhi_local", "apsystems_APSystens EZHI_offgrid_output_energy", "energy", "kWh", "total"),
    e("sensor.apsystens_ezhi_off_grid_input_energy", "apsystems_ezhi_local", "apsystems_APSystens EZHI_offgrid_input_energy", "energy", "kWh", "total"),
    e("sensor.apsystens_ezhi_device_temperature", "apsystems_ezhi_local", "apsystems_APSystens EZHI_device_temperature", "temperature", "°C", "measurement"),
    e("number.apsystems_apsystens_ezhi_on_grid_power", "apsystems_ezhi_local", "apsystems_APSystens EZHI_max_output_power", "power"),
    e("sensor.terrasse_apsystens_ezhi_power_limit", "apsystems_ezhi_local", "apsystems_APSystens EZHI_cloud_power_limit_state", "power", "W"),
    e("sensor.terrasse_apsystens_ezhi_control_transport", "apsystems_ezhi_local", "apsystems_APSystens EZHI_cloud_control_transport"),
    e("number.terrasse_apsystens_ezhi_soc_minimum", "apsystems_ezhi_local", "apsystems_APSystens EZHI_cloud_socmin", "battery", "%"),
    e("number.terrasse_apsystens_ezhi_soc_maximum", "apsystems_ezhi_local", "apsystems_APSystens EZHI_cloud_socmax", "battery", "%"),
    e("number.terrasse_apsystens_ezhi_preset_output_power", "apsystems_ezhi_local", "apsystems_APSystens EZHI_cloud_user_set_power", "power", "W"),
    e("number.terrasse_apsystens_ezhi_discharge_protection", "apsystems_ezhi_local", "apsystems_APSystens EZHI_cloud_discharge_protection", "battery", "%"),
    e("sensor.apsystens_ezhi_battery_power_inverted", "energy", "energy_power_battery_inverted_sensor_apsystens_ezhi_battery_power", "power", "W", "measurement"),
]
EM = [
    e("sensor.shellypro3em_aabbccddeeff_total_active_power", "shelly", "AABBCCDDEEFF-em:0-total_act_power", "power", "W", "measurement"),
    e("sensor.shellypro3em_aabbccddeeff_total_apparent_power", "shelly", "AABBCCDDEEFF-em:0-total_aprt_power", "apparent_power", "VA", "measurement"),
    e("sensor.shellypro3em_aabbccddeeff_total_current", "shelly", "AABBCCDDEEFF-em:0-total_current"),
    e("sensor.shellypro3em_aabbccddeeff_total_active_energy", "shelly", "AABBCCDDEEFF-emdata:0-total_act", "energy", "kWh", "total_increasing"),
    e("sensor.shellypro3em_aabbccddeeff_total_active_returned_energy", "shelly", "AABBCCDDEEFF-emdata:0-total_act_ret", "energy", "kWh", "total_increasing"),
    e("sensor.shellypro3em_aabbccddeeff_temperature", "shelly", "AABBCCDDEEFF-temperature:0-temperature_tc", "temperature", "°C", "measurement"),
]
PLUG = [
    e("sensor.shellyoutdoorsg3_112233445566_voltage", "shelly", "112233445566-switch:0-voltage"),
    e("sensor.shellyoutdoorsg3_112233445566_returned_energy", "shelly", "112233445566-switch:0-ret_energy"),
    e("sensor.solar_einspeisung_power", "shelly", "112233445566-switch:0-power", "power", "W", "measurement"),
    e("sensor.solar_einspeisung_energy", "shelly", "112233445566-switch:0-energy", "energy", "kWh", "total_increasing"),
    e("sensor.solar_einspeisung_consumed_energy", "shelly", "112233445566-switch:0-consumed_energy_switch"),
]
STORAGE_KEYS = ["pv_power", "pv_ac_power", "battery_power", "battery_soc", "output_power", "pv_energy",
                "battery_charge_energy", "battery_discharge_energy", "battery_capacity", "battery_soh",
                "battery_soc_min", "battery_soc_max", "battery_discharge_protection", "output_power_limit"]


def test_own_system():
    """Speicher, Netzmessung und Plug am Einspeisepunkt ergeben die heutige Zuordnung der eigenen Anlage."""
    storage, invert = suggest(EZHI, STORAGE_KEYS)
    assert storage == {
        "battery_capacity": "sensor.apsystens_ezhi_battery_capacity",
        "battery_charge_energy": "sensor.apsystens_ezhi_battery_total_charge_energy",
        "battery_discharge_energy": "sensor.apsystens_ezhi_battery_total_discharge_energy",
        "battery_discharge_protection": "number.terrasse_apsystens_ezhi_discharge_protection",
        "battery_power": "sensor.apsystens_ezhi_battery_power",
        "battery_soc": "sensor.apsystens_ezhi_battery_state_of_charge",
        "battery_soc_max": "number.terrasse_apsystens_ezhi_soc_maximum",
        "battery_soc_min": "number.terrasse_apsystens_ezhi_soc_minimum",
        "battery_soh": "sensor.apsystens_ezhi_battery_state_of_health",
        "output_power": "sensor.apsystens_ezhi_on_grid_power",
        "output_power_limit": "sensor.terrasse_apsystens_ezhi_power_limit",
        "pv_ac_power": "sensor.apsystens_ezhi_off_grid_power",
        "pv_energy": "sensor.apsystens_ezhi_photovoltaic_energy",
        "pv_power": "sensor.apsystens_ezhi_photovoltaic_power",
    }
    assert invert == ["output_power"]
    assert suggest(EM, ["grid_power"]) == ({"grid_power": "sensor.shellypro3em_aabbccddeeff_total_active_power"}, [])
    assert suggest(PLUG, ["output_energy"]) == ({"output_energy": "sensor.solar_einspeisung_energy"}, [])
    ez1 = [e("sensor.solar_ez1_m_gesamtleistung", "apsystems", "E07000000000_total_power"),
           e("sensor.solar_ez1_m_leistung_von_p1", "apsystems", "E07000000000_total_power_p1"),
           e("sensor.solar_ez1_m_gesamterzeugung_uber_lebensdauer", "apsystems", "E07000000000_lifetime_production")]
    assert suggest(ez1, ["pv_power", "pv_energy"]) == ({"pv_power": "sensor.solar_ez1_m_gesamtleistung",
                                                        "pv_energy": "sensor.solar_ez1_m_gesamterzeugung_uber_lebensdauer"}, [])


def test_without_profile():
    """Unbekanntes Gerät: eindeutige Zuordnung über Gerätedaten, mehrdeutige bleibt leer."""
    meter = [e("sensor.meter_power", "other", "x1", "power", "kW", "measurement"),
             e("sensor.meter_energy", "other", "x2", "energy", "kWh", "total_increasing"),
             e("sensor.meter_voltage", "other", "x3", "voltage", "V", "measurement")]
    assert suggest(meter, ["grid_power"]) == ({"grid_power": "sensor.meter_power"}, [])
    assert suggest(meter, ["pv_power", "pv_energy"]) == (
        {"pv_power": "sensor.meter_power", "pv_energy": "sensor.meter_energy"}, [])
    assert suggest(meter, ["pv_power", "battery_power"]) == ({}, [])  # zwei Größen, eine Entität
    two = meter + [e("sensor.meter_power_2", "other", "x4", "power", "W", "measurement")]
    assert suggest(two, ["grid_power"]) == ({}, [])  # zwei Kandidaten


def test_direction():
    assert direction(135) == "Südost 135°"
    assert direction(225) == "Südwest 225°"
    assert direction(350) == "Nord 350°"


def test_solarman():
    """Deye über beide Solarman-Integrationen, Muster aus deren Quellcode (unique_id-Bildung und Gerätedefinitionen)."""
    entry = "01k8z3m5q7r9t1v3w5x7y9a2b4"  # davidrapan: entry_id klein geschrieben, dann Name und Plattform
    hybrid = [e(f"sensor.deye_{n}", "solarman", f"{entry}_{n}_sensor") for n in (
        "pv_power", "pv1_power", "total_production", "total_production_1", "battery", "battery_power",
        "battery_state", "total_battery_charge", "total_battery_discharge", "battery_capacity", "grid_power",
        "grid_l1_power", "external_power", "power", "load_power")]
    found, invert = suggest(hybrid, ["grid_power"] + STORAGE_KEYS)
    assert found == {k: f"sensor.deye_{n}" for k, n in {
        "pv_power": "pv_power", "pv_energy": "total_production", "battery_soc": "battery",
        "battery_power": "battery_power", "battery_charge_energy": "total_battery_charge",
        "battery_discharge_energy": "total_battery_discharge", "battery_capacity": "battery_capacity",
        "grid_power": "grid_power", "output_power": "power"}.items()}
    assert invert == ["battery_power"]
    stephan = [e(f"sensor.deye_{i}", "solarman", f"Deye_2712345678_{n}") for i, n in enumerate((
        "PV1 Power", "Total Production", "Battery Power", "Battery SOC", "Total Battery Charge",
        "Total Battery Discharge", "Total Grid Power", "Total Load Power", "Total Power"))]
    found, invert = suggest(stephan, ["grid_power"] + STORAGE_KEYS)
    assert found == {"pv_energy": "sensor.deye_1", "battery_power": "sensor.deye_2", "battery_soc": "sensor.deye_3",
                     "battery_charge_energy": "sensor.deye_4", "battery_discharge_energy": "sensor.deye_5",
                     "grid_power": "sensor.deye_6", "output_power": "sensor.deye_8"}
    micro = [e("sensor.micro", "solarman", "Deye_4112345678_Total AC Output Power (Active)")]
    assert suggest(micro, ["pv_power"]) == ({"pv_power": "sensor.micro"}, [])


def test_huawei():
    """Huawei SUN2000 mit LUNA2000 und Power Meter, Muster aus wlcrs/huawei_solar und huawei-solar-lib."""
    keys = ("input_power", "active_power", "accumulated_yield_energy", "power_meter_active_power",
            "storage_charge_discharge_power", "storage_state_of_capacity", "storage_unit_1_state_of_capacity",
            "storage_total_charge", "storage_total_discharge", "storage_rated_capacity",
            "storage_discharging_cutoff_capacity", "storage_charging_cutoff_capacity")
    entities = [e(f"sensor.huawei_{k}", "huawei_solar", f"HV2150012345_{k}") for k in keys]
    found, invert = suggest(entities, ["grid_power"] + STORAGE_KEYS)
    assert found == {k: f"sensor.huawei_{n}" for k, n in {
        "pv_power": "input_power", "output_power": "active_power", "grid_power": "power_meter_active_power",
        "battery_power": "storage_charge_discharge_power", "battery_soc": "storage_state_of_capacity",
        "battery_charge_energy": "storage_total_charge", "battery_discharge_energy": "storage_total_discharge",
        "battery_capacity": "storage_rated_capacity", "battery_soc_min": "storage_discharging_cutoff_capacity",
        "battery_soc_max": "storage_charging_cutoff_capacity"}.items()}
    assert invert == ["grid_power"]


def test_hoymiles():
    """Hoymiles über OpenDTU, AhoyDTU und hoymiles_wifi, Muster aus deren Quellcode."""
    opendtu = [e(f"sensor.hm_{f.lower()}", "mqtt", f"116180212345_ch{c}_{f}") for c, f in (
        (0, "Power"), (0, "PowerDC"), (0, "YieldTotal"), (0, "YieldDay"), (1, "Power"), (1, "YieldTotal"))]
    assert suggest(opendtu, ["pv_power", "pv_energy"]) == (
        {"pv_power": "sensor.hm_power", "pv_energy": "sensor.hm_yieldtotal"}, [])
    ahoy = [e(f"sensor.ahoy_{i}", "mqtt", f"116180212345_ch{c}_{f}") for i, (c, f) in enumerate((
        (1, "P_DC"), (0, "P_AC"), (1, "YieldTotal"), (0, "YieldTotal")))]
    assert suggest(ahoy, ["pv_power", "pv_energy"]) == ({"pv_power": "sensor.ahoy_1", "pv_energy": "sensor.ahoy_3"}, [])
    wifi = [e("sensor.hms_power", "hoymiles_wifi", "hoymiles_01k8z3m5q7r9t1v3w5x7y9a2b4_dtu_power"),
            e("sensor.hms_port", "hoymiles_wifi", "hoymiles_01k8z3m5q7r9t1v3w5x7y9a2b4_pv_data[0].power")]
    assert suggest(wifi, ["pv_power"]) == ({"pv_power": "sensor.hms_power"}, [])


def test_anker_solix():
    """Anker Solarbank über ha-anker-solix, Muster aus dem Quellcode (unique_id <Kontext>_<Schlüssel>)."""
    keys = ("input_power", "battery_power_signed", "bat_charge_power", "state_of_charge", "state_of_charge_total",
            "ac_to_home_load", "home_demand_total", "solar_energy")
    entities = [e(f"sensor.sb_{k}", "anker_solix", f"apc1a00012345678_{k}") for k in keys]
    assert suggest(entities, STORAGE_KEYS) == ({
        "pv_power": "sensor.sb_input_power", "battery_power": "sensor.sb_battery_power_signed",
        "battery_soc": "sensor.sb_state_of_charge", "output_power": "sensor.sb_ac_to_home_load"}, [])


def test_zendure():
    """Zendure Hyper/SolarFlow über Zendure-HA, Muster aus dem Quellcode (snake_case aus Gerätename und Eigenschaft)."""
    names = ("solar_input_power", "aggr_solar", "bat_in_out", "output_pack_power", "pack_input_power",
             "electric_level", "aggr_charge", "aggr_discharge", "total_kwh", "available_kwh", "min_soc", "soc_set",
             "output_home_power", "aggr_output_home", "grid_input_power", "output_limit", "input_limit")
    entities = [e(f"sensor.hyper_{n}", "zendure_ha", f"hyper_2000_{n}") for n in names]
    found, invert = suggest(entities, STORAGE_KEYS + ["output_energy"])
    assert found == {k: f"sensor.hyper_{n}" for k, n in {
        "pv_power": "solar_input_power", "pv_energy": "aggr_solar", "battery_power": "bat_in_out",
        "battery_soc": "electric_level", "battery_charge_energy": "aggr_charge",
        "battery_discharge_energy": "aggr_discharge", "battery_capacity": "total_kwh", "battery_soc_min": "min_soc",
        "battery_soc_max": "soc_set", "output_power": "output_home_power", "output_energy": "aggr_output_home",
        "output_power_limit": "output_limit"}.items()}
    assert invert == ["battery_power"]
