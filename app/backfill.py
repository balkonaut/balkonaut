"""Verlauf aus Home Assistant als Stundenwerte nachtragen.

Aufruf im Container: docker compose exec balkonaut python -m app.backfill [tage]
"""
import os
import sys
import time
from pathlib import Path

from app import config
from balkonaut.homeassistant import HomeAssistant
from balkonaut.storage import Storage


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    data = Path(os.environ.get("BALKONAUT_DATA", "data"))
    ha = config.load(data / "config.yaml")["home_assistant"]
    adapter = HomeAssistant(ha["url"], ha["token"], {k: tuple(v) for k, v in ha["entities"].items()})
    storage = Storage(data / "balkonaut.db")
    until = storage.first() or int(time.time()) // 3600 * 3600
    start = (until - days * 86400) // 3600 * 3600
    hours = storage.backfill(adapter.history(start, until), start, until)
    print(f"{hours} Stunden nachgetragen")


if __name__ == "__main__":
    main()
