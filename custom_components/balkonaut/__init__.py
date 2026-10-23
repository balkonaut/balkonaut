"""Balkonaut: Bilanz, Amortisation und Akku-Auswertung als Sensoren.

Zwei Betriebsarten: Werte von einer laufenden Balkonaut-App abholen (Adresse) oder eigenständig in Home Assistant
messen, speichern und rechnen (Entitäten). Die Rechenlogik kommt in beiden Fällen aus core/ (balkonaut-Paket).
"""
import asyncio
from datetime import UTC, date, datetime, timedelta
from functools import partial
import json
import logging
from pathlib import Path
import time

import aiohttp
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_URL, Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er, issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.loader import async_get_integration

from .core import analytics, views
from .core.homeassistant import normalize
from .core.storage import Storage

DOMAIN = "balkonaut"
DEFAULT_SCAN_INTERVAL = 5  # Minuten
FAILURES_BEFORE_ISSUE = 3  # so viele Abfragen in Folge ohne Antwort, bis HA einen Reparaturhinweis zeigt
SAMPLE_INTERVAL = timedelta(seconds=10)  # wie der Collector der App
CONF_ENTITIES = "entities"
CONF_INVERT = "invert"
BACKFILLED = "backfilled"  # Verlauf aus dem Recorder schon übernommen
# Messgrößen, die Balkonaut aus Home-Assistant-Entitäten liest (Bedeutung: Handbuch, Einstellungen)
KEYS = ["grid_power", "pv_power", "pv_ac_power", "battery_power", "battery_soc", "output_power", "output_energy",
        "pv_energy", "battery_charge_energy", "battery_discharge_energy", "battery_capacity", "battery_soh",
        "battery_soc_min", "battery_soc_max", "battery_discharge_protection", "output_power_limit",
        "pv_forecast_today", "pv_ac_forecast_today"]
SIGNED_KEYS = ["grid_power", "pv_power", "pv_ac_power", "battery_power", "output_power"]
PLATFORMS = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]
STATIC_URL = "/balkonaut_static"  # Karte und Panel aus frontend/, getrennt vom Panel-Pfad /balkonaut
CARD_URL = f"{STATIC_URL}/balkonaut-card.js"
PANEL = "balkonaut"  # Pfad des Panels in der Seitenleiste
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
_LOGGER = logging.getLogger(__name__)

type BalkonautConfigEntry = ConfigEntry[BalkonautCoordinator]


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """Gemeinsames Gerät aller Balkonaut-Entitäten."""
    return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="Balkonaut", manufacturer="Balkonaut",
                      entry_type=DeviceEntryType.SERVICE, configuration_url=entry.data.get(CONF_URL))


async def fetch_status(session: aiohttp.ClientSession, url: str) -> dict:
    """Status der Balkonaut-App abrufen (/api/v1/status)."""
    async with session.get(f"{url}/api/v1/status", timeout=aiohttp.ClientTimeout(total=30)) as resp:
        resp.raise_for_status()
        data = await resp.json()
    if "bilanz" not in data:
        raise ValueError("keine Balkonaut-Antwort")
    return data


class BalkonautCoordinator(DataUpdateCoordinator[dict]):
    """Fragt /api/v1/status der Balkonaut-App ab oder rechnet ihn eigenständig aus der eigenen Datenbank."""

    def __init__(self, hass: HomeAssistant, entry: BalkonautConfigEntry, storage: Storage | None = None) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        self.url = entry.data.get(CONF_URL)
        self.storage = storage
        self.lock = asyncio.Lock()  # SQLite-Zugriffe nacheinander, sie laufen im Executor
        self.failures = 0

    async def _async_update_data(self) -> dict:
        if self.storage:
            self._check_entities()
            return await self._local_status()
        issue_id = f"unreachable_{self.config_entry.entry_id}"
        try:
            data = await fetch_status(async_get_clientsession(self.hass), self.url)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            self.failures += 1
            if self.failures == FAILURES_BEFORE_ISSUE:
                ir.async_create_issue(self.hass, DOMAIN, issue_id, is_fixable=False, severity=ir.IssueSeverity.WARNING,
                                      translation_key="unreachable", translation_placeholders={"url": self.url})
            raise UpdateFailed(f"Balkonaut unter {self.url} nicht erreichbar: {err}") from err
        if self.failures >= FAILURES_BEFORE_ISSUE:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        self.failures = 0
        return data

    def _check_entities(self) -> None:
        """Reparaturhinweis für zugeordnete Entitäten, die es nicht mehr gibt, z. B. weil die Hersteller-Integration
        sie umbenannt hat. Nicht verfügbare Entitäten zählen nicht, sie kommen meist von selbst wieder."""
        if not self.hass.is_running:  # beim Start fehlen Zustände, bis alle Integrationen geladen sind
            return
        registry = er.async_get(self.hass)
        missing = [eid for eid in self.config_entry.data[CONF_ENTITIES].values() if self.hass.states.get(eid) is None
                   and (not (reg := registry.async_get(eid)) or reg.disabled_by)]
        issue_id = f"missing_entities_{self.config_entry.entry_id}"
        if missing:
            ir.async_create_issue(self.hass, DOMAIN, issue_id, is_fixable=False, severity=ir.IssueSeverity.WARNING,
                                  translation_key="missing_entities",
                                  translation_placeholders={"entities": ", ".join(missing)})
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    @property
    def prices(self) -> dict:
        opts = self.config_entry.options
        return {"energy": opts.get("energy", 0.0), "feed_in": opts.get("feed_in", 0.0)}

    @property
    def commissioned(self) -> date | None:
        return date.fromisoformat(day) if (day := self.config_entry.options.get("commissioned")) else None

    async def async_compute(self, func, *args):
        """func(storage, *args) im Executor, nacheinander mit den Schreibzugriffen; Ergebnis in JSON-Form wie die App."""
        async with self.lock:
            data = await self.hass.async_add_executor_job(func, self.storage, *args)
        return json.loads(json.dumps(data, default=str))

    async def _local_status(self) -> dict:
        def status(storage, now):
            return analytics.status(storage.hourly(int(now)), storage.latest(), now, self.prices,
                                    self.config_entry.options.get("cost", 0.0), self.commissioned)
        return await self.async_compute(status, time.time())

    async def async_store_regulation(self, _now=None) -> None:
        """Regelgüte abgeschlossener Tage sichern, solange die Rohwerte noch da sind (für den Monatsbericht)."""
        await self.async_compute(views.store_regulation_days, self.prices, time.time())

    def _factor(self, key: str) -> int:
        return -1 if key in self.config_entry.data.get(CONF_INVERT, []) else 1

    async def async_backfill(self) -> None:
        """Einmalig den Verlauf aus dem Recorder als Stundenwerte vor der ersten eigenen Messung übernehmen."""
        from homeassistant.components.recorder import get_instance, history

        recorder = get_instance(self.hass)
        until = await self.hass.async_add_executor_job(self.storage.first) or int(time.time()) // 3600 * 3600
        start = until - recorder.keep_days * 86400
        entities = self.config_entry.data[CONF_ENTITIES]
        states = await recorder.async_add_executor_job(partial(
            history.get_significant_states, self.hass, datetime.fromtimestamp(start, UTC),
            datetime.fromtimestamp(until, UTC), list(entities.values()), significant_changes_only=False,
            no_attributes=True))
        series = {}
        for key, entity_id in entities.items():
            # Verlauf ohne Attribute: Einheit der aktuellen Entität, wie beim Import der App
            unit = getattr(self.hass.states.get(entity_id), "attributes", {}).get("unit_of_measurement")
            series[key] = sorted((s.last_changed.timestamp(), normalize(
                {"state": s.state, "attributes": {"unit_of_measurement": unit}}, self._factor(key)))
                for s in states.get(entity_id, []))
        async with self.lock:
            hours = await self.hass.async_add_executor_job(self.storage.backfill, series, start, until)
        _LOGGER.info("Balkonaut: %s Stunden aus dem Verlauf von Home Assistant übernommen", hours)
        self.hass.config_entries.async_update_entry(self.config_entry, data={**self.config_entry.data, BACKFILLED: True})
        await self.async_request_refresh()

    async def async_sample(self, _now=None) -> None:
        """Aktuelle Zustände der Entitäten normalisieren und speichern, abgeschlossene Stunden aggregieren."""
        values = {}
        for key, entity_id in self.config_entry.data[CONF_ENTITIES].items():
            state = self.hass.states.get(entity_id)
            values[key] = normalize(state and {"state": state.state, "attributes": state.attributes},
                                    self._factor(key))
        ts = int(time.time())
        async with self.lock:
            await self.hass.async_add_executor_job(_store, self.storage, ts, values)


def _store(storage: Storage, ts: int, values: dict) -> None:
    storage.add(ts, values)
    storage.aggregate(ts)


def _open_storage(path: Path) -> Storage:
    path.parent.mkdir(exist_ok=True)
    return Storage(path)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """WebSocket-Befehl und Lovelace-Karte, unabhängig von den Einträgen."""
    for command in (ws_status, ws_history, ws_report, ws_regulation):
        websocket_api.async_register_command(hass, command)

    async def import_from_app(call: ServiceCall) -> ServiceResponse:
        """Historie einer Balkonaut-App (Docker oder Add-on) in den eigenständigen Eintrag übernehmen."""
        entry = _entry(hass, None)
        if entry is None or not entry.runtime_data.storage:
            raise HomeAssistantError("Kein eigenständiger Balkonaut-Eintrag eingerichtet")
        url = call.data[CONF_URL].strip().rstrip("/")
        try:
            async with async_get_clientsession(hass).get(f"{url}/api/v1/export",
                                                         timeout=aiohttp.ClientTimeout(total=300)) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise HomeAssistantError(f"Balkonaut-App unter {url} nicht erreichbar: {err}") from err
        hours = await entry.runtime_data.async_compute(lambda storage: storage.merge(data))
        _LOGGER.info("Balkonaut: %s Stunden aus der App unter %s übernommen", hours, url)
        await entry.runtime_data.async_request_refresh()
        return {"stunden": hours}

    hass.services.async_register(DOMAIN, "import_from_app", import_from_app, schema=vol.Schema(
        {vol.Required(CONF_URL): cv.url}), supports_response=SupportsResponse.OPTIONAL)
    if "http" in hass.config.components:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), cache_headers=False)])
    if "frontend" in hass.config.components:  # Karte ohne manuellen Ressourcen-Eintrag laden
        from homeassistant.components.frontend import add_extra_js_url

        version = (await async_get_integration(hass, DOMAIN)).version
        add_extra_js_url(hass, f"{CARD_URL}?v={version}")
        hass.data[DOMAIN] = version
    return True


def _entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    """Geladener Eintrag mit entry_id, ohne Angabe der eigenständige, sonst der erste."""
    entries = sorted(hass.config_entries.async_loaded_entries(DOMAIN), key=lambda e: CONF_ENTITIES not in e.data)
    return next((e for e in entries if e.entry_id == (entry_id or e.entry_id)), None)


@websocket_api.websocket_command({vol.Required("type"): "balkonaut/status", vol.Optional("entry_id"): str})
@callback
def ws_status(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Status für Karte und Panel: berechnete Werte und, im eigenständigen Betrieb, die zugeordneten Entitäten
    für Live-Werte."""
    if (entry := _entry(hass, msg.get("entry_id"))) is None:
        connection.send_error(msg["id"], "not_found", "Kein Balkonaut-Eintrag geladen")
        return
    connection.send_result(msg["id"], {
        "entry_id": entry.entry_id, "entities": entry.data.get(CONF_ENTITIES), "invert": entry.data.get(CONF_INVERT, []),
        "status": entry.runtime_data.data,
        "names": {"hub": _hub_name(hass, entry), "battery": entry.options.get("battery_name") or None}})


def _hub_name(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Modell des Geräts hinter den PV- bzw. Akku-Entitäten, z. B. EZHI; None, wenn keins bekannt ist."""
    entities, entity_reg, device_reg = entry.data.get(CONF_ENTITIES) or {}, er.async_get(hass), dr.async_get(hass)
    for key in ("pv_power", "battery_power", "battery_soc"):
        if (e := entity_reg.async_get(entities.get(key, ""))) and e.device_id \
                and (device := device_reg.async_get(e.device_id)) and device.model:
            return device.model
    return None


async def _view(hass, connection, msg, path: str, params: dict, compute) -> None:
    """Ansicht eigenständig aus der eigenen Datenbank rechnen oder von der Balkonaut-App holen (/api/v1/<path>)."""
    if (entry := _entry(hass, msg.get("entry_id"))) is None:
        connection.send_error(msg["id"], "not_found", "Kein Balkonaut-Eintrag geladen")
        return
    coordinator = entry.runtime_data
    if coordinator.storage:
        connection.send_result(msg["id"], await coordinator.async_compute(compute, coordinator, time.time()))
        return
    try:
        async with async_get_clientsession(hass).get(f"{coordinator.url}/api/v1/{path}", params=params,
                                                     timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            connection.send_result(msg["id"], await resp.json())
    except (aiohttp.ClientError, TimeoutError) as err:
        connection.send_error(msg["id"], "unreachable", f"Balkonaut-App nicht erreichbar: {err}")


@websocket_api.websocket_command({vol.Required("type"): "balkonaut/verlauf", vol.Optional("entry_id"): str,
                                  vol.Optional("ansicht", default="tag"): str, vol.Optional("datum", default=""): str})
@websocket_api.async_response
async def ws_history(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    await _view(hass, connection, msg, "verlauf", {"ansicht": msg["ansicht"], "datum": msg["datum"]},
                lambda storage, c, now: views.history(storage, msg["ansicht"], msg["datum"], c.prices, now))


@websocket_api.websocket_command({vol.Required("type"): "balkonaut/bericht", vol.Optional("entry_id"): str,
                                  vol.Optional("monat", default=""): str})
@websocket_api.async_response
async def ws_report(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    await _view(hass, connection, msg, "bericht", {"monat": msg["monat"]},
                lambda storage, c, now: views.report(storage, msg["monat"], c.prices, now, None, c.commissioned))


@websocket_api.websocket_command({vol.Required("type"): "balkonaut/nulleinspeisung", vol.Optional("entry_id"): str})
@websocket_api.async_response
async def ws_regulation(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    await _view(hass, connection, msg, "nulleinspeisung", {},
                lambda storage, c, now: views.regulation_week(storage, c.prices, now))


async def async_setup_entry(hass: HomeAssistant, entry: BalkonautConfigEntry) -> bool:
    storage = None
    if CONF_ENTITIES in entry.data:
        storage = await hass.async_add_executor_job(_open_storage, Path(hass.config.path(DOMAIN, "balkonaut.db")))
    coordinator = BalkonautCoordinator(hass, entry, storage)
    if storage:
        await coordinator.async_sample()
        entry.async_on_unload(async_track_time_interval(hass, coordinator.async_sample, SAMPLE_INTERVAL))
        entry.async_on_unload(async_track_time_interval(hass, coordinator.async_store_regulation, timedelta(hours=1)))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if storage and not entry.data.get(BACKFILLED) and "recorder" in hass.config.components:
        entry.async_create_background_task(hass, coordinator.async_backfill(), "balkonaut_backfill")
    if "frontend" in hass.config.components:
        from homeassistant.components import panel_custom
        from homeassistant.components.frontend import DATA_PANELS

        if PANEL not in hass.data[DATA_PANELS]:
            await panel_custom.async_register_panel(
                hass, frontend_url_path=PANEL, webcomponent_name="balkonaut-panel", sidebar_title="Balkonaut",
                sidebar_icon="mdi:solar-power-variant", module_url=f"{STATIC_URL}/balkonaut-panel.js?v={hass.data[DOMAIN]}")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BalkonautConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and "frontend" in hass.config.components and not [
            e for e in hass.config_entries.async_loaded_entries(DOMAIN) if e.entry_id != entry.entry_id]:
        from homeassistant.components.frontend import async_remove_panel

        async_remove_panel(hass, PANEL)  # letzter Eintrag weg: Panel aus der Seitenleiste nehmen
    if unloaded and (storage := entry.runtime_data.storage):
        async with entry.runtime_data.lock:
            await hass.async_add_executor_job(storage.db.close)
    return unloaded
