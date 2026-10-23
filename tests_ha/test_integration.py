from pathlib import Path

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_URL
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.balkonaut import DOMAIN

URL = "http://balkonaut.local:8000"
STATUS = {
    "warnungen": [],
    "bilanz": {p: {"ersparnis": 1.25, "erzeugung": 3.4, "eigenverbrauch": 3.0, "netzbezug": 5.0,
                   "autarkiegrad": 0.375} for p in ("tag", "monat", "jahr", "gesamt")},
    "akku": {p: {"zyklen_gesamt": 154.1, "gesundheit": 100.0, "wirkungsgrad": 0.98} for p in ("tag", "monat", "jahr", "gesamt")},
    "amortisation": {"bisher_gespart": 480.2, "rest": 969.8, "ersparnis_pro_jahr": 270.5, "amortisiert_am": "2029-06-09"},
}


async def start_flow(hass, step):
    """Einrichtung starten und im Menü die Betriebsart wählen."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": step})


async def test_config_flow(hass, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/v1/status", json=STATUS)
    result = await start_flow(hass, "app")
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: f" {URL}/ "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_URL: URL}


async def test_config_flow_cannot_connect(hass, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/v1/status", status=500)
    result = await start_flow(hass, "app")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL})
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "cannot_connect"}


async def test_sensors_and_options(hass, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/v1/status", json=STATUS)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: URL})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)

    def state(key):  # Entitäts-IDs hängen von der Sprache ab, die eindeutige Kennung nicht
        return hass.states.get(registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{key}")).state

    assert state("ersparnis_tag") == "1.25"
    assert state("autarkie_tag") == "37.5"
    assert state("amortisiert_am") == "2029-06-09"
    assert state("vollzyklen") == "154.1"
    assert state("akku_wirkungsgrad") == "98.0"
    assert len(hass.states.async_entity_ids("sensor")) == 22

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_SCAN_INTERVAL: 10})
    assert result["type"] is FlowResultType.CREATE_ENTRY and entry.options[CONF_SCAN_INTERVAL] == 10


async def test_warnings(hass, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/v1/status", json=STATUS)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: URL})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    problem = registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_warnungen")
    event = registry.async_get_entity_id("event", DOMAIN, f"{entry.entry_id}_warnung")
    assert hass.states.get(problem).state == "off"
    assert hass.states.get(event).state == "unknown"

    warning = {"code": "ungleich", "wechselrichter": "ac", "text": "zweiter Wechselrichter bleibt zurück"}
    entry.runtime_data.async_set_updated_data(STATUS | {"warnungen": [warning]})
    await hass.async_block_till_done()
    assert hass.states.get(problem).state == "on"
    assert hass.states.get(problem).attributes["warnungen"] == [warning["text"]]
    fired = hass.states.get(event)
    assert fired.attributes["event_type"] == "warnung" and fired.attributes["text"] == warning["text"]

    entry.runtime_data.async_set_updated_data(STATUS | {"warnungen": [warning]})  # gleiche Warnung: kein neues Ereignis
    await hass.async_block_till_done()
    assert hass.states.get(event).state == fired.state


async def test_unreachable_issue_and_diagnostics(hass, aioclient_mock):
    from homeassistant.helpers import issue_registry as ir
    from custom_components.balkonaut.diagnostics import async_get_config_entry_diagnostics
    aioclient_mock.get(f"{URL}/api/v1/status", json=STATUS)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: URL})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    coordinator = entry.runtime_data
    issues = ir.async_get(hass)
    issue_id = f"unreachable_{entry.entry_id}"

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/status", status=500)
    for _ in range(3):
        await coordinator.async_refresh()
    assert issues.async_get_issue(DOMAIN, issue_id) is not None

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/status", json=STATUS)
    await coordinator.async_refresh()
    assert issues.async_get_issue(DOMAIN, issue_id) is None

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["data"][CONF_URL] == "**REDACTED**" and diag["status"]["bilanz"]["tag"]["ersparnis"] == 1.25


def device(hass, platform, name, entities):
    """Gerät mit Entitäten und Zuständen anlegen: entities = [(unique_id, entity_id, state, attributes)]."""
    from homeassistant.helpers import device_registry as dr
    owner = MockConfigEntry(domain=platform)
    owner.add_to_hass(hass)
    dev = dr.async_get(hass).async_get_or_create(config_entry_id=owner.entry_id, identifiers={(platform, name)}, name=name)
    for unique_id, entity_id, state, attrs in entities:
        domain, object_id = entity_id.split(".")
        er.async_get(hass).async_get_or_create(domain, platform, unique_id, suggested_object_id=object_id,
                                               device_id=dev.id, config_entry=owner)
        hass.states.async_set(entity_id, state, attrs)
    return dev.id


async def test_standalone(hass):
    """Geführte Einrichtung: Geräte wählen, Vorschlag mit aktuellen Werten prüfen, Zusammenfassung, einrichten."""
    power = {"device_class": "power", "unit_of_measurement": "W", "state_class": "measurement"}
    ezhi = device(hass, "apsystems_ezhi_local", "EZHI", [
        ("apsystems_EZHI_battery_soc", "sensor.soc", "50", {"device_class": "battery", "unit_of_measurement": "%"}),
        ("apsystems_EZHI_ongrid_power", "sensor.abgabe", "-0.2", power | {"unit_of_measurement": "kW"})])
    em = device(hass, "shelly", "3EM", [("AA-em:0-total_act_power", "sensor.netz", "300", power),
                                        ("AA-em:0-total_aprt_power", "sensor.schein", "320", power | {"device_class": "apparent_power"})])
    solar = MockConfigEntry(domain="forecast_solar", subentries_data=[
        {"data": {"azimuth": 135}, "subentry_type": "plane", "title": "Ost", "unique_id": None}])
    solar.add_to_hass(hass)
    er.async_get(hass).async_get_or_create("sensor", "forecast_solar", f"{solar.entry_id}_energy_production_today",
                                           suggested_object_id="prognose", config_entry=solar)
    result = await start_flow(hass, "standalone")
    assert result["step_id"] == "standalone"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"storage_device": ezhi, "grid_device": em})
    assert result["step_id"] == "entities"
    values = result["description_placeholders"]["values"]
    assert "300 W (Bezug)" in values and "house: 200 W\n" in values and "50 %" in values
    form = {"grid": {"grid_power": "sensor.netz"}, "generation": {}, "battery": {"battery_soc": "sensor.soc"},
            "output": {"output_power": "sensor.abgabe"}, "forecast": {"pv_forecast_today": "sensor.prognose"},
            "invert": ["output_power"]}
    for sec, fields in form.items():  # Vorschlag aus den Geräteprofilen
        if sec != "invert":
            schema = result["data_schema"].schema[sec].schema.schema
            assert {k.schema: k.description["suggested_value"] for k in schema if k.description} == fields
    assert "(Südost 135°)" in values
    empty = {sec: {} for sec in form if sec != "invert"}
    assert (await hass.config_entries.flow.async_configure(result["flow_id"], empty))["errors"] == {"base": "no_entities"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], form)
    assert result["type"] is FlowResultType.MENU and result["step_id"] == "summary"
    assert "Akku-Auswertung" in result["description_placeholders"]["available"]
    assert "Ertragswächter" in result["description_placeholders"]["available"]
    assert "Erzeugung" in result["description_placeholders"]["missing"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "create"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"entities": {"grid_power": "sensor.netz", "battery_soc": "sensor.soc",
                                           "output_power": "sensor.abgabe", "pv_forecast_today": "sensor.prognose"},
                              "invert": ["output_power"]}
    await hass.async_block_till_done()
    assert (await start_flow(hass, "standalone"))["reason"] == "already_configured"  # nur eine eigene Datenbank

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    coordinator = entry.runtime_data
    latest = await hass.async_add_executor_job(coordinator.storage.latest)
    assert {k: v for k, (_, v) in latest.items()} == {"battery_soc": 50, "output_power": 200, "grid_power": 300}
    assert coordinator.data["live"]["output_power"] == 200 and "tag" in coordinator.data["bilanz"]
    assert len(hass.states.async_entity_ids("sensor")) == 4 + 22
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_standalone_options(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    hass.states.async_set("sensor.soc", "50", {"unit_of_measurement": "%"})
    entry = MockConfigEntry(domain=DOMAIN, unique_id="standalone", data={"entities": {"battery_soc": "sensor.soc"}, "invert": []})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    form = {CONF_SCAN_INTERVAL: 5, "energy": 0.32, "feed_in": 0.0, "cost": 1450}
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], form | {"commissioned": "2099-01-01"})
    assert result["errors"] == {"commissioned": "future_date"}
    result = await hass.config_entries.options.async_configure(result["flow_id"], form | {"commissioned": "2024-05-01"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()  # Neustart mit den neuen Optionen
    assert entry.runtime_data.data["amortisation"]["kosten"] == 1450
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_reconfigure(hass, aioclient_mock):
    """Neu konfigurieren ändert Zuordnung oder Adresse, Eintrag und Messdaten bleiben."""
    hass.states.async_set("sensor.soc", "50", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.netz", "300", {"unit_of_measurement": "W"})
    entry = MockConfigEntry(domain=DOMAIN, unique_id="standalone", data={
        "entities": {"battery_soc": "sensor.soc"}, "invert": [], "backfilled": True})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    db = hass.config.path(DOMAIN, "balkonaut.db")
    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "entities" and "50 %" in result["description_placeholders"]["values"]
    form = {"grid": {"grid_power": "sensor.netz"}, "generation": {}, "battery": {"battery_soc": "sensor.soc"},
            "output": {}, "forecast": {}, "invert": []}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], form)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "create"})
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.data == {"entities": {"grid_power": "sensor.netz", "battery_soc": "sensor.soc"}, "invert": [],
                          "backfilled": True}
    assert hass.config_entries.async_entries(DOMAIN) == [entry] and Path(db).exists()
    assert await hass.config_entries.async_unload(entry.entry_id)

    aioclient_mock.get(f"{URL}/api/v1/status", json=STATUS)
    aioclient_mock.get("http://neu:8000/api/v1/status", json=STATUS)
    app = MockConfigEntry(domain=DOMAIN, data={CONF_URL: URL})
    app.add_to_hass(hass)
    result = await app.start_reconfigure_flow(hass)
    assert result["step_id"] == "app"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: "http://neu:8000/"})
    assert result["reason"] == "reconfigure_successful" and app.data == {CONF_URL: "http://neu:8000"}


async def test_missing_entity_issue(hass):
    """Fehlt eine zugeordnete Entität, erscheint ein Reparaturhinweis; nicht verfügbar reicht dafür nicht."""
    from homeassistant.helpers import issue_registry as ir
    hass.states.async_set("sensor.soc", "unavailable")
    entry = MockConfigEntry(domain=DOMAIN, unique_id="standalone", data={
        "entities": {"battery_soc": "sensor.soc", "grid_power": "sensor.weg"}, "invert": [], "backfilled": True})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"missing_entities_{entry.entry_id}")
    assert issue.translation_placeholders == {"entities": "sensor.weg"}
    hass.states.async_set("sensor.weg", "300", {"unit_of_measurement": "W"})
    await entry.runtime_data.async_refresh()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"missing_entities_{entry.entry_id}") is None
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_standalone_backfill(hass, freezer):
    from datetime import timedelta
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done
    now = dt_util.utcnow().replace(minute=30, second=0, microsecond=0)
    freezer.move_to(now - timedelta(hours=5))  # Verlauf vor der Einrichtung: 5 Stunden lang 400 W Netzbezug
    hass.states.async_set("sensor.netz", "400", {"unit_of_measurement": "W"})
    await async_wait_recording_done(hass)
    freezer.move_to(now)
    entry = MockConfigEntry(domain=DOMAIN, unique_id="standalone", data={"entities": {"grid_power": "sensor.netz"}, "invert": []})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.data["backfilled"]
    hourly = await hass.async_add_executor_job(entry.runtime_data.storage.hourly)
    hours = [h for key, h, mean, *_ in hourly if key == "grid_power" and mean == 400]
    assert len(hours) >= 4  # volle Stunden vor der ersten eigenen Messung
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_websocket_and_card(hass, hass_ws_client, hass_client):
    hass.states.async_set("sensor.soc", "50", {"unit_of_measurement": "%"})
    entry = MockConfigEntry(domain=DOMAIN, unique_id="standalone",
                            data={"entities": {"battery_soc": "sensor.soc"}, "invert": ["output_power"]})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "balkonaut/status"})
    msg = await ws.receive_json()
    assert msg["success"] and msg["result"]["entities"] == {"battery_soc": "sensor.soc"}
    assert msg["result"]["invert"] == ["output_power"] and "tag" in msg["result"]["status"]["bilanz"]
    await ws.send_json({"id": 2, "type": "balkonaut/status", "entry_id": "gibt-es-nicht"})
    assert (await ws.receive_json())["error"]["code"] == "not_found"
    for i, (cmd, key) in enumerate([("verlauf", "balken"), ("bericht", "tage"), ("nulleinspeisung", None)], start=3):
        await ws.send_json({"id": i, "type": f"balkonaut/{cmd}"})
        msg = await ws.receive_json()
        assert msg["success"] and (key is None or key in msg["result"]), cmd
    client = await hass_client()
    for name in ("balkonaut-card.js", "balkonaut-panel.js"):
        resp = await client.get(f"/balkonaut_static/{name}")
        assert resp.status == 200 and "customElements.define" in await resp.text()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_views_from_app(hass, hass_ws_client, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/v1/status", json=STATUS)
    aioclient_mock.get(f"{URL}/api/v1/verlauf?ansicht=woche&datum=", json={"balken": [], "titel": "KW 43"})
    aioclient_mock.get(f"{URL}/api/v1/nulleinspeisung", status=500)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: URL})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "balkonaut/verlauf", "ansicht": "woche"})
    assert (await ws.receive_json())["result"]["titel"] == "KW 43"  # von der App durchgereicht
    await ws.send_json({"id": 2, "type": "balkonaut/nulleinspeisung"})
    assert (await ws.receive_json())["error"]["code"] == "unreachable"


async def test_import_from_app(hass, aioclient_mock):
    hass.states.async_set("sensor.netz", "300", {"unit_of_measurement": "W"})
    entry = MockConfigEntry(domain=DOMAIN, unique_id="standalone", data={"entities": {"grid_power": "sensor.netz"}, "invert": []})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    export = {"hourly": [["grid_power", 3600, 500.0, 500.0, 0.0, None, 360]], "regulation": {"1970-01-01": {"tage": 1}}}
    aioclient_mock.get(f"{URL}/api/v1/export", json=export)
    result = await hass.services.async_call(DOMAIN, "import_from_app", {CONF_URL: URL}, blocking=True, return_response=True)
    assert result == {"stunden": 1}
    hourly = await hass.async_add_executor_job(entry.runtime_data.storage.hourly)
    assert ("grid_power", 3600, 500.0, 500.0, 0.0, None) in hourly
    assert await hass.config_entries.async_unload(entry.entry_id)
