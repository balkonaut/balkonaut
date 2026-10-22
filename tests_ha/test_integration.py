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


async def test_standalone(hass):
    hass.states.async_set("sensor.soc", "50", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.abgabe", "-0.2", {"unit_of_measurement": "kW"})
    hass.states.async_set("sensor.netz", "300", {"unit_of_measurement": "W"})
    result = await start_flow(hass, "standalone")
    assert (await hass.config_entries.flow.async_configure(result["flow_id"], {}))["errors"] == {"base": "no_entities"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "battery_soc": "sensor.soc", "output_power": "sensor.abgabe", "grid_power": "sensor.netz", "invert": ["output_power"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"entities": {"grid_power": "sensor.netz", "battery_soc": "sensor.soc",
                                           "output_power": "sensor.abgabe"}, "invert": ["output_power"]}
    await hass.async_block_till_done()
    assert (await start_flow(hass, "standalone"))["reason"] == "already_configured"  # nur eine eigene Datenbank

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    coordinator = entry.runtime_data
    latest = await hass.async_add_executor_job(coordinator.storage.latest)
    assert {k: v for k, (_, v) in latest.items()} == {"battery_soc": 50, "output_power": 200, "grid_power": 300}
    assert coordinator.data["live"]["output_power"] == 200 and "tag" in coordinator.data["bilanz"]
    assert len(hass.states.async_entity_ids("sensor")) == 3 + 22
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
