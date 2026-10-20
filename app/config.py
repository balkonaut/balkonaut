"""Konfiguration aus config.yaml im Datenverzeichnis."""
from datetime import date

import yaml

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
    # ponytail: safe_dump verwirft Kommentare in config.yaml; ruamel.yaml, falls das stört
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))


def commissioned(cfg):
    """Datum der Inbetriebnahme als date oder None (YAML liefert date oder Text)."""
    value = cfg["system"]["commissioned"]
    return date.fromisoformat(value) if isinstance(value, str) else value
