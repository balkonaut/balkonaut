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


def _collect(rows, start):
    """Summen ab start: Wh je Messgröße (+/- Anteile), Zählerzuwächse und Stundenwerte je Messgröße."""
    wh = defaultdict(float)
    counter = {}
    prev = {}
    hours = defaultdict(dict)
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
            hours[key][hour] = (mean, pos, neg, last)

    def energy(counter_key, power_key):
        return counter[counter_key] if counter_key in counter else wh[power_key] / 1000

    return wh, counter, hours, energy


def balance(rows, start, prices):
    """rows: (key, hour, mean, mean_pos, mean_neg, last), sortiert nach key und hour. Energie in kWh."""
    wh, counter, hours, energy = _collect(rows, start)
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


def battery(rows, start, prices):
    """Akku-Auswertung ab start: Zyklen, Gesundheit, Wirkungsgrad, Zeiten mit vollem/leerem Akku."""
    wh, counter, hours, energy = _collect(rows, start)

    def first(key):
        return hours[key][min(hours[key])][3] if hours.get(key) else None

    def latest(key):
        return hours[key][max(hours[key])][3] if hours.get(key) else None

    cap = latest("battery_capacity")
    charge, discharge = counter.get("battery_charge_energy"), counter.get("battery_discharge_energy")
    soc0, soc1 = first("battery_soc"), latest("battery_soc")
    efficiency = None
    if cap and charge and charge > 0.5 and discharge is not None and None not in (soc0, soc1):
        efficiency = (discharge + (soc1 - soc0) / 100 * cap) / charge
    inputs = energy("pv_energy", "pv_power") + (wh["pv_ac_power"] + wh["output_power-"]) / 1000 + (discharge or 0)
    outputs = energy("output_energy", "output_power+") + (charge or 0)

    soc_max, soc_min = latest("battery_soc_max") or 100, latest("battery_soc_min") or 0
    full = empty = 0
    export_full = import_empty = 0.0
    for hour, (soc, *_) in hours.get("battery_soc", {}).items():
        _, pos, neg, _ = hours["grid_power"].get(hour, (0, 0, 0, None))
        if soc >= soc_max - 2:
            full += 1
            export_full -= neg / 1000
        elif soc <= soc_min + 2:
            empty += 1
            import_empty += pos / 1000
    return {
        "zyklen": discharge / cap if cap and discharge is not None else None,
        "zyklen_gesamt": latest("battery_discharge_energy") / cap if cap and latest("battery_discharge_energy") else None,
        "gesundheit": latest("battery_soh"),
        "kapazitaet": cap,
        "wirkungsgrad": efficiency,
        "verluste_wechselrichter": 1 - outputs / inputs if inputs > 0.5 else None,
        "stunden_voll": full,
        "einspeisung_bei_vollem_akku": export_full,
        "stunden_leer": empty,
        "netzbezug_bei_leerem_akku": import_empty,
        "kosten_bei_leerem_akku": import_empty * prices["energy"],
    }
