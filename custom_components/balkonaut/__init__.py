"""Balkonaut: Bilanz, Amortisation und Akku-Auswertung aus der Balkonaut-App als Sensoren."""
from datetime import timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

DOMAIN = "balkonaut"
DEFAULT_SCAN_INTERVAL = 5  # Minuten
PLATFORMS = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)

type BalkonautConfigEntry = ConfigEntry[BalkonautCoordinator]


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

    async def _async_update_data(self) -> dict:
        try:
            return await fetch_status(async_get_clientsession(self.hass), self.url)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Balkonaut unter {self.url} nicht erreichbar: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: BalkonautConfigEntry) -> bool:
    coordinator = BalkonautCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BalkonautConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
