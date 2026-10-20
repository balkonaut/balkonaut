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


async def test_config_flow(hass, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/v1/status", json=STATUS)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: f" {URL}/ "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_URL: URL}


async def test_config_flow_cannot_connect(hass, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/v1/status", status=500)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
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
