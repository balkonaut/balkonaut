"""Auswertung aus den Stundenwerten: Energiebilanz, Ersparnis und Amortisation.

Begriffe und Formeln: docs/auswertung.md
"""
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")  # ponytail: feste Zeitzone, konfigurierbar machen für Nutzer außerhalb DE/AT


def periods(now):
    """Beginn von heute, diesem Monat, diesem Jahr (Ortszeit) und gesamt als Zeitstempel."""
    day = datetime.fromtimestamp(now, TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return {"tag": day.timestamp(), "monat": day.replace(day=1).timestamp(),
            "jahr": day.replace(month=1, day=1).timestamp(), "gesamt": 0}


def balance(rows, start, prices):
    """rows: (key, hour, mean, mean_pos, mean_neg, last), sortiert nach key und hour. Energie in kWh."""
    wh = defaultdict(float)
    counter = {}
    prev = {}
    for key, hour, mean, pos, neg, last in rows:
        if last is not None and key.endswith("_energy"):
            if hour >= start:
                counter.setdefault(key, 0.0)
                if key in prev and last > prev[key]:  # Rücksetzungen des Zählers ignorieren
                    counter[key] += last - prev[key]
            prev[key] = last
        if hour >= start:
            wh[key] += mean
            wh[key + "+"] += pos
            wh[key + "-"] -= neg

    def energy(counter_key, power_key):
        return counter[counter_key] if counter_key in counter else wh[power_key] / 1000

    grid_import, grid_export = wh["grid_power+"] / 1000, wh["grid_power-"] / 1000
    output = energy("output_energy", "output_power+")
    self_use = max(output - grid_export, 0.0)
    consumption = grid_import + self_use
    return {
        "erzeugung": energy("pv_energy", "pv_power") + wh["pv_ac_power"] / 1000,
        "abgabe": output,
        "netzbezug": grid_import,
        "einspeisung": grid_export,
        "eigenverbrauch": self_use,
        "hausverbrauch": consumption,
        "eigenverbrauchsquote": self_use / output if output else None,
        "autarkiegrad": self_use / consumption if consumption else None,
        "ersparnis": self_use * prices["energy"] + grid_export * prices["feed_in"],
    }


def amortization(rows, prices, cost):
    """Bisherige Ersparnis und Restlaufzeit bis zur Amortisation.

    Bisherige Ersparnis: Stand des Abgabezählers (seit Zählerstart, meist seit Inbetriebnahme)
    mal gemessener Eigenverbrauchsquote mal Arbeitspreis; ohne Zähler nur der Messzeitraum.
    Jährliche Ersparnis: Tagesdurchschnitt des Messzeitraums mal 365.
    """
    # ponytail: Hochrechnung ohne Saisonverlauf, Herbstdaten unterschätzen das Jahr. Prognose ab P3.
    total = balance(rows, 0, prices)
    hours = [h for _, h, *_ in rows]
    days = (max(hours) - min(hours) + 3600) / 86400 if hours else 0
    per_year = total["ersparnis"] / days * 365 if days else 0.0
    meter = [last for key, _, _, _, _, last in rows if key == "output_energy" and last is not None]
    if meter and total["eigenverbrauchsquote"] is not None:
        saved = meter[-1] * total["eigenverbrauchsquote"] * prices["energy"]
    else:
        saved = total["ersparnis"]
    remaining = max(cost - saved, 0.0)
    return {
        "kosten": cost,
        "bisher_gespart": saved,
        "ersparnis_pro_jahr": per_year,
        "rest": remaining,
        "jahre_bis_amortisation": remaining / per_year if per_year else None,
        "messtage": days,
    }
