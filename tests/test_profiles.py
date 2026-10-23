from balkonaut.profiles import suggest


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
FORECAST = [
    e("sensor.energy_production_today", "forecast_solar", "entry_a_energy_production_today", "energy", "kWh"),
    e("sensor.energy_production_tomorrow", "forecast_solar", "entry_a_energy_production_tomorrow", "energy", "kWh"),
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
    assert suggest(FORECAST, ["pv_forecast_today"]) == ({"pv_forecast_today": "sensor.energy_production_today"}, [])
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
