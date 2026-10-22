"""Einrichtung der Balkonaut-Integration: eigenständig mit Entitäten oder mit der Adresse einer Balkonaut-App."""
from datetime import date
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    DateSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
)

from . import CONF_ENTITIES, CONF_INVERT, DEFAULT_SCAN_INTERVAL, DOMAIN, KEYS, SIGNED_KEYS, fetch_status


class BalkonautConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["standalone", "app"])

    async def async_step_standalone(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Eigenständig: Entitäten je Messgröße wählen, Balkonaut misst und speichert in Home Assistant."""
        await self.async_set_unique_id("standalone")  # eine eigene Datenbank, also nur ein eigenständiger Eintrag
        self._abort_if_unique_id_configured()
        errors = {}
        if user_input is not None:
            entities = {k: user_input[k] for k in KEYS if user_input.get(k)}
            if entities:
                return self.async_create_entry(title="Balkonaut", data={
                    CONF_ENTITIES: entities, CONF_INVERT: user_input.get(CONF_INVERT, [])})
            errors["base"] = "no_entities"
        entity = EntitySelector(EntitySelectorConfig(domain=["sensor", "number", "input_number"]))
        schema = {vol.Optional(k): entity for k in KEYS}
        schema[vol.Optional(CONF_INVERT, default=[])] = SelectSelector(SelectSelectorConfig(
            options=SIGNED_KEYS, multiple=True, translation_key=CONF_INVERT))
        return self.async_show_form(step_id="standalone", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_app(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Mit einer laufenden Balkonaut-App (Docker oder Add-on) über deren Adresse."""
        errors = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            self._async_abort_entries_match({CONF_URL: url})
            try:
                await fetch_status(async_get_clientsession(self.hass), url)
            except (aiohttp.ClientError, TimeoutError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Balkonaut", data={CONF_URL: url})
        return self.async_show_form(
            step_id="app",
            data_schema=vol.Schema({vol.Required(CONF_URL, default="http://"): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BalkonautOptionsFlow:
        return BalkonautOptionsFlow()


class BalkonautOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            day = user_input.get("commissioned")
            if day and date.fromisoformat(day) > date.today():
                errors["commissioned"] = "future_date"
            else:
                return self.async_create_entry(data=user_input)
        schema = {vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=60))}
        if CONF_ENTITIES in self.config_entry.data:  # eigenständig: Preise und Kosten hier statt in der App
            def number(unit, step):
                return NumberSelector(NumberSelectorConfig(min=0, step=step, mode=NumberSelectorMode.BOX,
                                                           unit_of_measurement=unit))
            schema |= {vol.Required("energy", default=0.0): number("€/kWh", "any"),
                       vol.Required("feed_in", default=0.0): number("€/kWh", "any"),
                       vol.Required("cost", default=0.0): number("€", 1),
                       vol.Optional("commissioned"): DateSelector()}
        return self.async_show_form(step_id="init", errors=errors, data_schema=self.add_suggested_values_to_schema(
            vol.Schema(schema), user_input or self.config_entry.options))
