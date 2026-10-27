"""Einrichtung der Balkonaut-Integration mit Entitäten und/oder Geräten per Adresse."""
from datetime import date
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    DateSelector,
    DeviceSelector,
    DeviceSelectorConfig,
    EntityFilterSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
)
from homeassistant.helpers.translation import async_get_translations

from . import CONF_DEVICES, CONF_ENTITIES, CONF_INVERT, DEFAULT_SCAN_INTERVAL, DOMAIN, KEYS, PLANES, SIGNED_KEYS
from .core.devices import Devices, detect
from .core.homeassistant import normalize
from .core.profiles import PROFILES, direction, suggest

ROLES = ["grid_device", "storage_device", "extra_device", "output_device"]  # Geräte im ersten Schritt
# Abschnitte der Zuordnung im zweiten Schritt, zusammen genau KEYS
SECTIONS = {
    "grid": ["grid_power"],
    "generation": ["pv_power", "pv_energy", "pv_ac_power"],
    "battery": ["battery_power", "battery_soc", "battery_charge_energy", "battery_discharge_energy",
                "battery_capacity", "battery_soh", "battery_soc_min", "battery_soc_max", "battery_discharge_protection"],
    "output": ["output_power", "output_energy", "output_power_limit"],
    "forecast": ["pv_forecast_today", "pv_ac_forecast_today"],
}
STORAGE_KEYS = [k for k in KEYS if k not in SECTIONS["grid"] + SECTIONS["forecast"]]
# Vereinfachung: Texte nur deutsch wie das Handbuch; in die Übersetzungen, sobald es eine zweite Sprache gibt
# Funktion -> benötigte Messgrößen, je Eintrag reicht eine der Alternativen
FEATURES = {
    "Bilanz mit Netzbezug, Einspeisung und Ersparnis": [("grid_power",)],
    "Abgabe des Balkonkraftwerks ins Haus": [("output_energy", "output_power")],
    "Erzeugung und Energiefluss": [("pv_energy", "pv_power", "pv_ac_power")],
    "Akku-Auswertung und Akku-Ring": [("battery_soc",)],
    "Regelgüte der Nulleinspeisung": [("grid_power",), ("output_power",)],
    "Ertragswächter mit Prognose": [("pv_forecast_today", "pv_ac_forecast_today")],
}
SIGNS = {"grid_power": ("Bezug", "Einspeisung"), "battery_power": ("lädt", "entlädt"),
         "output_power": ("", "Bezug, Vorzeichen prüfen"),
         "pv_power": ("", "negativ, Vorzeichen prüfen"), "pv_ac_power": ("", "negativ, Vorzeichen prüfen")}


class BalkonautConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self.async_step_standalone(user_input)

    async def async_step_standalone(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Eigenständig, Schritt 1: Geräte wählen, aus ihnen schlägt Balkonaut die Entitäten vor."""
        await self.async_set_unique_id("standalone")  # eine eigene Datenbank, also nur ein eigenständiger Eintrag
        self._abort_if_unique_id_configured()
        if user_input is not None:
            self._entities, self._invert = self._suggest(user_input)
            self._devices, self._device_values = [], {}
            return await self.async_step_entities()
        device = DeviceSelector(DeviceSelectorConfig(entity=[EntityFilterSelectorConfig(domain="sensor")]))
        return self.async_show_form(step_id="standalone", data_schema=vol.Schema({vol.Optional(r): device for r in ROLES}))

    async def async_step_entities(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Schritt 2: Vorschläge prüfen und ergänzen, mit aktuellen Werten zur Kontrolle."""
        errors = {}
        if user_input is not None:
            entities = {k: v for sec in SECTIONS for k, v in user_input.get(sec, {}).items() if v}
            hosts = [h.strip() for h in user_input.get("hosts", "").split(",") if h.strip()]
            try:
                self._devices = [{"type": await self.hass.async_add_executor_job(detect, h), "host": h} for h in hosts]
            except ValueError:
                errors["hosts"] = "unknown_device"
            else:
                self._device_values = await self.hass.async_add_executor_job(Devices(self._devices).read)
                if entities or self._devices:
                    self._entities = entities
                    self._invert = [k for k in user_input.get(CONF_INVERT, [])
                                    if k in entities or self._device_values.get(k) is not None]
                    return await self.async_step_summary()
                errors["base"] = "no_entities"
        entity = EntitySelector(EntitySelectorConfig(domain=["sensor", "number", "input_number"]))
        # Geräte, die Balkonaut selbst abfragt, ohne Integration des Herstellers; zuerst, für Anlagen ohne Entitäten
        schema = {vol.Optional("hosts", default=""): str}
        schema |= {vol.Required(sec): section(
            vol.Schema({vol.Optional(k): entity for k in keys}),
            {"collapsed": bool(self._entities) and not any(k in self._entities for k in keys)})
            for sec, keys in SECTIONS.items()}
        schema[vol.Optional(CONF_INVERT, default=[])] = SelectSelector(SelectSelectorConfig(
            options=SIGNED_KEYS, multiple=True, translation_key=CONF_INVERT))
        suggested = {sec: {k: self._entities[k] for k in keys if k in self._entities} for sec, keys in SECTIONS.items()}
        return self.async_show_form(
            step_id="entities", errors=errors, description_placeholders={"values": await self._values()},
            data_schema=self.add_suggested_values_to_schema(vol.Schema(schema), suggested | {
                CONF_INVERT: self._invert, "hosts": ", ".join(d["host"] for d in self._devices)}))

    async def async_step_summary(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Schritt 3: was mit dieser Zuordnung geht und was nicht, dann einrichten oder zurück."""
        have = set(self._entities) | {k for k, v in self._device_values.items() if v is not None}
        ok = [name for name, needs in FEATURES.items() if all(have & set(alt) for alt in needs)]
        return self.async_show_menu(step_id="summary", menu_options=["create", "entities"], description_placeholders={
            "available": "\n".join(f"- {n}" for n in ok) or "–",
            "missing": "\n".join(f"- {n}" for n in FEATURES if n not in ok) or "–",
            "values": await self._values()})

    async def async_step_create(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        data = {CONF_ENTITIES: self._entities, CONF_INVERT: self._invert}
        if self._devices:
            data[CONF_DEVICES] = self._devices
        if self.source == SOURCE_RECONFIGURE:  # Datenbank bleibt, sie hängt nicht am Eintrag
            return self.async_update_reload_and_abort(self._get_reconfigure_entry(), data_updates=data)
        return self.async_create_entry(title="Balkonaut", data=data)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Zuordnung oder Adressen ändern, ohne den Eintrag und seine Messdaten zu löschen."""
        entry = self._get_reconfigure_entry()
        self._entities, self._invert = dict(entry.data[CONF_ENTITIES]), list(entry.data.get(CONF_INVERT, []))
        self._devices = list(entry.data.get(CONF_DEVICES, []))
        self._device_values = (await self.hass.async_add_executor_job(Devices(self._devices).read)
                               if self._devices else {})
        return await self.async_step_entities()

    def _suggest(self, devices: dict[str, str]) -> tuple[dict[str, str], list[str]]:
        """Vorschlag aus den gewählten Geräten; spezifische Rollen zuerst, damit sie Vorrang haben."""
        registry = er.async_get(self.hass)
        found, invert = {}, []

        def add(entries, keys, rename=None):
            entities = []
            for e in entries:
                attrs = getattr(self.hass.states.get(e.entity_id), "attributes", {})
                entities.append({"entity_id": e.entity_id, "platform": e.platform, "unique_id": e.unique_id,
                                 "device_class": attrs.get("device_class"),
                                 "unit_of_measurement": attrs.get("unit_of_measurement"),
                                 "state_class": attrs.get("state_class")})
            rename = rename or {}
            keys = [k for k in keys if rename.get(k, k) not in found]
            new, flip = suggest(entities, keys)
            found.update({rename.get(k, k): v for k, v in new.items()})
            invert.extend(rename.get(k, k) for k in flip)

        def device(role):
            return er.async_entries_for_device(registry, devices[role]) if devices.get(role) else []

        add(device("grid_device"), ["grid_power"])
        add(device("output_device"), ["output_energy"])  # Zähler am Einspeisepunkt ist maßgeblich (Handbuch, Messquellen)
        add(device("extra_device"), ["pv_power"], {"pv_power": "pv_ac_power"})
        add(device("storage_device"), STORAGE_KEYS)
        add(device("output_device"), ["output_power"])
        # Entitäten ohne Gerät (z. B. Modbus-Vorlagen in YAML), nur wenn ein Profil sie genau kennt
        add([e for e in registry.entities.values() if not e.device_id and not e.disabled_by
             and any(re.search(p, e.unique_id) for p, _, _ in PROFILES.get(e.platform, []))],
            ["grid_power"] + STORAGE_KEYS)
        if len(forecasts := self._forecasts()) == 1 and "pv_ac_power" not in found:  # bei zwei Erzeugern unklar, welcher
            found["pv_forecast_today"] = next(iter(forecasts))
        return found, invert

    def _forecasts(self) -> dict[str, str]:
        """Prognose-Entitäten von Forecast.Solar mit der Ausrichtung ihrer Flächen, z. B. „Südost 150°“."""
        out = {}
        for e in er.async_get(self.hass).entities.values():
            if e.platform == "forecast_solar" and e.unique_id.endswith("_energy_production_today") and not e.disabled_by:
                entry = self.hass.config_entries.async_get_entry(e.config_entry_id)
                planes = entry.get_subentries_of_type("plane") if entry else []
                out[e.entity_id] = " + ".join(direction(p.data["azimuth"]) for p in planes) or e.entity_id
        return out

    async def _values(self) -> str:
        """Aktuelle Werte der zugeordneten Entitäten, mit gedrehtem Vorzeichen, damit Fehler auffallen."""
        labels = await async_get_translations(self.hass, self.hass.config.language, "config", [DOMAIN])
        forecasts = self._forecasts()
        lines = []
        for sec, keys in SECTIONS.items():
            for key in keys:
                label = labels.get(f"component.{DOMAIN}.config.step.entities.sections.{sec}.data.{key}", key)
                if key in self._entities:
                    where = f" ({forecasts[self._entities[key]]})" if self._entities[key] in forecasts else ""
                    lines.append(f"- {label}: {self._live(key)}{where}")
                elif self._device_values.get(key) is not None:
                    lines.append(f"- {label}: {self._live(key)} (Gerät)")
        return "\n".join(lines) or "–"

    def _live(self, key: str) -> str:
        sign = -1 if key in self._invert else 1
        if key in self._entities:
            state = self.hass.states.get(self._entities[key])
            value = normalize(state and {"state": state.state, "attributes": state.attributes}, sign)
        else:
            value = sign * self._device_values[key]
        if value is None:
            return "kein Wert"
        unit = "W" if key.endswith(("_power", "_limit")) else "kWh" if key.endswith(("_energy", "_today", "_capacity")) else "%"
        text = f"{abs(value) if key in SIGNS else value:.{1 if unit == 'kWh' else 0}f} {unit}".replace(".", ",")
        if key in SIGNS and round(value) and (word := SIGNS[key][value < 0]):
            text += f" ({word})"
        return text

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
            elif any(0 < len(user_input.get(key) or {}) < 3 for key in PLANES):
                errors["base"] = "incomplete_plane"
            else:
                return self.async_create_entry(data=user_input)
        schema = {vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=60)), vol.Optional("battery_name"): str, vol.Optional("extra_name"): str}
        if CONF_ENTITIES in self.config_entry.data:  # eigenständig: Preise und Kosten hier statt in der App
            def number(unit, step, low=0, **high):
                return NumberSelector(NumberSelectorConfig(min=low, step=step, mode=NumberSelectorMode.BOX,
                                                           unit_of_measurement=unit, **high))
            schema |= {vol.Required("energy", default=0.0): number("€/kWh", "any"),
                       vol.Required("feed_in", default=0.0): number("€/kWh", "any"),
                       vol.Required("cost", default=0.0): number("€", 1),
                       vol.Optional("commissioned"): DateSelector()}
            # Flächen für die Prognose ohne Forecast.Solar-Integration, je Wechselrichter eine
            # Vereinfachung: eine Fläche je Wechselrichter, mehrere bei Nachfrage, spätestens 31.01.2027 prüfen
            # Grenzen wie in den Einstellungen der App
            plane = vol.Schema({vol.Optional("declination"): number("°", 1, 0, max=90),
                                vol.Optional("azimuth"): number("°", 1, 0, max=360),
                                vol.Optional("kwp"): number("kWp", "any", 0.01, max=100)})
            schema |= {vol.Optional(key): section(plane, {"collapsed": not self.config_entry.options.get(key)})
                       for key in PLANES}
        return self.async_show_form(step_id="init", errors=errors, data_schema=self.add_suggested_values_to_schema(
            vol.Schema(schema), user_input or self.config_entry.options))
