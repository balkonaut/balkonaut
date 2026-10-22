"""Balkonaut: Bilanz, Amortisation und Akku-Auswertung als Sensoren.

Zwei Betriebsarten: Werte von einer laufenden Balkonaut-App abholen (Adresse) oder eigenständig in Home Assistant
messen, speichern und rechnen (Entitäten). Die Rechenlogik kommt in beiden Fällen aus core/ (balkonaut-Paket).
"""
import asyncio
from datetime import date, timedelta
import json
import logging
from pathlib import Path
import time

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .core import analytics
from .core.homeassistant import normalize
from .core.storage import Storage

DOMAIN = "balkonaut"
DEFAULT_SCAN_INTERVAL = 5  # Minuten
FAILURES_BEFORE_ISSUE = 3  # so viele Abfragen in Folge ohne Antwort, bis HA einen Reparaturhinweis zeigt
SAMPLE_INTERVAL = timedelta(seconds=10)  # wie der Collector der App
CONF_ENTITIES = "entities"
CONF_INVERT = "invert"
# Messgrößen, die Balkonaut aus Home-Assistant-Entitäten liest (Bedeutung: Handbuch, Einstellungen)
KEYS = ["grid_power", "pv_power", "pv_ac_power", "battery_power", "battery_soc", "output_power", "output_energy",
        "pv_energy", "battery_charge_energy", "battery_discharge_energy", "battery_capacity", "battery_soh",
        "battery_soc_min", "battery_soc_max", "battery_discharge_protection", "output_power_limit",
        "pv_forecast_today", "pv_ac_forecast_today"]
SIGNED_KEYS = ["grid_power", "pv_power", "pv_ac_power", "battery_power", "output_power"]
PLATFORMS = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]
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

    async def _local_status(self) -> dict:
        now = time.time()
        opts = self.config_entry.options
        async with self.lock:
            rows, latest = await self.hass.async_add_executor_job(
                lambda: (self.storage.hourly(int(now)), self.storage.latest()))
        data = await self.hass.async_add_executor_job(
            analytics.status, rows, latest, now, {"energy": opts.get("energy", 0.0), "feed_in": opts.get("feed_in", 0.0)},
            opts.get("cost", 0.0), date.fromisoformat(day) if (day := opts.get("commissioned")) else None)
        return json.loads(json.dumps(data, default=str))  # gleiche Form wie die Antwort der App (Datum als Text)

    async def async_sample(self, _now=None) -> None:
        """Aktuelle Zustände der Entitäten normalisieren und speichern, abgeschlossene Stunden aggregieren."""
        invert = set(self.config_entry.data.get(CONF_INVERT, []))
        values = {}
        for key, entity_id in self.config_entry.data[CONF_ENTITIES].items():
            state = self.hass.states.get(entity_id)
            values[key] = normalize(state and {"state": state.state, "attributes": state.attributes},
                                    -1 if key in invert else 1)
        ts = int(time.time())
        async with self.lock:
            await self.hass.async_add_executor_job(_store, self.storage, ts, values)


def _store(storage: Storage, ts: int, values: dict) -> None:
    storage.add(ts, values)
    storage.aggregate(ts)


def _open_storage(path: Path) -> Storage:
    path.parent.mkdir(exist_ok=True)
    return Storage(path)


async def async_setup_entry(hass: HomeAssistant, entry: BalkonautConfigEntry) -> bool:
    storage = None
    if CONF_ENTITIES in entry.data:
        storage = await hass.async_add_executor_job(_open_storage, Path(hass.config.path(DOMAIN, "balkonaut.db")))
    coordinator = BalkonautCoordinator(hass, entry, storage)
    if storage:
        await coordinator.async_sample()
        entry.async_on_unload(async_track_time_interval(hass, coordinator.async_sample, SAMPLE_INTERVAL))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BalkonautConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and (storage := entry.runtime_data.storage):
        async with entry.runtime_data.lock:
            await hass.async_add_executor_job(storage.db.close)
    return unloaded
