"""Balkonaut: Bilanz, Amortisation und Akku-Auswertung aus der Balkonaut-App als Sensoren."""
from datetime import timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

DOMAIN = "balkonaut"
DEFAULT_SCAN_INTERVAL = 5  # Minuten
FAILURES_BEFORE_ISSUE = 3  # so viele Abfragen in Folge ohne Antwort, bis HA einen Reparaturhinweis zeigt
PLATFORMS = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)

type BalkonautConfigEntry = ConfigEntry[BalkonautCoordinator]


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """Gemeinsames Gerät aller Balkonaut-Entitäten."""
    return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="Balkonaut", manufacturer="Balkonaut",
                      entry_type=DeviceEntryType.SERVICE, configuration_url=entry.data[CONF_URL])


async def fetch_status(session: aiohttp.ClientSession, url: str) -> dict:
    """Status der Balkonaut-App abrufen (/api/v1/status)."""
    async with session.get(f"{url}/api/v1/status", timeout=aiohttp.ClientTimeout(total=30)) as resp:
        resp.raise_for_status()
        data = await resp.json()
    if "bilanz" not in data:
        raise ValueError("keine Balkonaut-Antwort")
    return data


class BalkonautCoordinator(DataUpdateCoordinator[dict]):
    """Fragt /api/v1/status der Balkonaut-App ab."""

    def __init__(self, hass: HomeAssistant, entry: BalkonautConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        self.url = entry.data[CONF_URL]
        self.failures = 0

    async def _async_update_data(self) -> dict:
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


async def async_setup_entry(hass: HomeAssistant, entry: BalkonautConfigEntry) -> bool:
    coordinator = BalkonautCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BalkonautConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
