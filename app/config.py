"""Konfiguration aus config.yaml im Datenverzeichnis."""
import os
from datetime import date
from pathlib import Path

import yaml

from balkonaut.devices import Devices
from balkonaut.homeassistant import HomeAssistant

DEFAULTS = {
    "prices": {"energy": 0.0, "feed_in": 0.0},  # €/kWh
    "system": {"cost": 0.0, "commissioned": None},  # Anschaffungskosten in €, Inbetriebnahme (Datum)
}


def load(path):
    cfg = (yaml.safe_load(path.read_text()) if path.exists() else None) or {}
    for section, values in DEFAULTS.items():
        cfg[section] = {**values, **(cfg.get(section) or {})}
    return cfg


def save(path, cfg):
    # Vereinfachung: safe_dump verwirft Kommentare in config.yaml; ruamel.yaml, falls das stört
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))


def commissioned(cfg):
    """Datum der Inbetriebnahme als date oder None (YAML liefert date oder Text)."""
    value = cfg["system"]["commissioned"]
    return date.fromisoformat(value) if isinstance(value, str) else value


def data_dir():
    """Datenverzeichnis mit config.yaml und Datenbank (im Container /data)."""
    return Path(os.environ.get("BALKONAUT_DATA", "data"))


def adapter(cfg):
    """Geräte direkt (Abschnitt devices) oder über Home Assistant (Abschnitt home_assistant), sonst None."""
    if devices := cfg.get("devices"):
        return Devices(devices, cfg.get("location"), cfg.get("planes") or ())
    if ha := cfg.get("home_assistant"):
        return HomeAssistant(ha["url"], ha["token"], {k: tuple(v) for k, v in ha["entities"].items()},
                             cfg.get("location"), cfg.get("planes") or ())
    return None
