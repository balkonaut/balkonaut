"""Auswertungen für die Ansichten Verlauf, Bericht und Nulleinspeisung, gemeinsam für Docker-App und Integration.

storage: balkonaut.storage.Storage, now: Unix-Zeit, prices: {"energy", "feed_in"} in €/kWh.
"""
from datetime import date, datetime, timedelta

from . import analytics
from .storage import RAW_DAYS

VIEWS = {"tag": "Tag", "woche": "Woche", "monat": "Monat", "jahr": "Jahr"}
REGULATION_KEYS = ["grid_power", "output_power", "pv_ac_power", "battery_soc"]


def parse_day(text, today):
    """Datum aus Text (JJJJ-MM-TT), bei leerer oder ungültiger Angabe today."""
    try:
        return date.fromisoformat(text) if text else today
    except ValueError:
        return today


def history(storage, view, datum, prices, now):
    """Balken einer Verlaufsansicht (tag, woche, monat, jahr) und Bilanz des Zeitraums."""
    today = datetime.fromtimestamp(now, analytics.TZ).date()
    view = view if view in VIEWS else "tag"
    title, buckets, prev, nxt = analytics.buckets(view, parse_day(datum, today))
    rows = storage.hourly(int(now))
    return {"ansicht": view, "titel": title, "zurueck": prev, "weiter": nxt if nxt <= today else None,
            "balken": analytics.history(rows, buckets, prices),
            "bilanz": analytics.balance([r for r in rows if r[1] < buckets[-1][2]], buckets[0][1], prices)}


def report(storage, monat, prices, now, profile=None, commissioned=None):
    """Monatsbericht (monat=JJJJ-MM, sonst der laufende Monat) mit gespeicherter Regelgüte der Tage."""
    today = datetime.fromtimestamp(now, analytics.TZ).date()
    day = parse_day(monat + "-01" if monat else "", today)
    r = analytics.month_report(storage.hourly(int(now)), day, prices, now, profile, commissioned)
    if r["weiter"] > today:
        r["weiter"] = None
    first = day.replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    r["nulleinspeisung"] = analytics.combine_regulation(
        storage.regulation_days(first.isoformat(), last.isoformat()).values())
    return r


def regulation(storage, prices, start, end):
    """Regelgüte der Nulleinspeisung aus den Rohwerten in [start, end), None ohne Messwerte."""
    latest = {k: v for k, (_, v) in storage.latest().items() if v is not None}
    return analytics.regulation(storage.series(start, REGULATION_KEYS, end), prices,
                                soc_min=latest.get("battery_soc_min", 10), limit=latest.get("output_power_limit", 800))


def regulation_week(storage, prices, now):
    """Regelgüte der letzten 7 Tage."""
    return regulation(storage, prices, int(now) - 7 * 86400, now)


def store_regulation_days(storage, prices, now):
    """Regelgüte für jeden abgeschlossenen Tag mit Rohwerten berechnen, der noch nicht gespeichert ist."""
    today = datetime.fromtimestamp(now, analytics.TZ).date()
    days = [today - timedelta(days=i) for i in range(RAW_DAYS - 1, 0, -1)]
    stored = storage.regulation_days(days[0].isoformat(), days[-1].isoformat())
    for day in days:
        if day.isoformat() not in stored:
            # Tagesende über Ortszeit: bei Zeitumstellung hat der Tag 23 oder 25 Stunden
            if r := regulation(storage, prices, analytics._ts(day), analytics._ts(day + timedelta(days=1))):
                storage.save_regulation_day(day.isoformat(), r)
