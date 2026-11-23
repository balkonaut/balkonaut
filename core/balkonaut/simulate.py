"""Simulator: Energiefluss Stunde für Stunde aus gemessenem Hausverbrauch und PV-Erzeugung nachrechnen.

Grundlage sind die Stundenwerte (Mittelwert in W = Wh je Stunde). Hausverbrauch = Abgabe + Netz, PV = beide
Wechselrichter. Modell der Nulleinspeisung: PV deckt das Haus bis zum Abgabelimit, Überschuss lädt den Akku, der Rest
geht bis zum Limit ins Netz, darüber wird abgeregelt; fehlt Leistung, entlädt der Akku bis zur Untergrenze.
Ladevorrang: Manche Speicher (EZHI) laden auch dann, wenn das Haus den Strom gerade selbst bräuchte; dieser Anteil wird
aus der Messung bestimmt (calibrate), sonst trifft die Simulation zwar den Netzbezug, aber nicht die Akku-Zyklen.
Vereinfachung: Stundenmittel, Lastspitzen innerhalb einer Stunde sieht das Modell nicht; genauer ginge es nur mit den
Rohwerten, die nach 14 Tagen gelöscht werden.
"""
from dataclasses import dataclass, replace

KEYS = ("grid_power", "output_power", "pv_power", "pv_ac_power")


@dataclass(frozen=True)
class Anlage:
    capacity: float = 0.0  # kWh nutzbare Nennkapazität, 0 = ohne Akku
    soc_min: float = 10.0  # %
    soc_max: float = 100.0  # %
    limit: float = 800.0  # W Abgabelimit
    efficiency: float = 0.92  # je Richtung (Laden, Entladen)
    standby: float = 0.0  # W, die der Wechselrichter ohne Abgabe aus dem Haus zieht
    pv_factor: float = 1.0  # Skalierung der Erzeugung (mehr oder weniger Module)
    charge_first: float = 0.0  # Anteil der direkt nutzbaren PV, den der Speicher trotzdem zuerst lädt


def hours(rows, start=None, end=None):
    """[(Stunde, PV Wh, Haus Wh)] aus Stundenwerten; Stunden ohne Netz- oder Abgabemessung fehlen."""
    by = {}
    for key, hour, mean, *_ in rows:
        if key in KEYS and (start is None or hour >= start) and (end is None or hour < end) and mean is not None:
            by.setdefault(hour, {})[key] = mean
    return [(hour, max(v.get("pv_power", 0) + v.get("pv_ac_power", 0), 0), max(v["output_power"] + v["grid_power"], 0))
            for hour, v in sorted(by.items()) if "grid_power" in v and "output_power" in v]


def simulate(series, anlage, soc0=None):
    """series: [(Stunde, PV Wh, Haus Wh)]. soc0: Ladestand zu Beginn in %, sonst Untergrenze.
    Gibt Summen in kWh zurück: Netzbezug, Einspeisung, Abgabe ins Haus, geladen, entladen, abgeregelt."""
    a = anlage
    cap = a.capacity * 1000
    lo, hi = cap * a.soc_min / 100, cap * a.soc_max / 100
    soc = cap * (a.soc_min if soc0 is None else min(max(soc0, a.soc_min), a.soc_max)) / 100
    tot = dict.fromkeys(("netzbezug", "einspeisung", "ins_haus", "geladen", "entladen", "abgeregelt"), 0.0)
    for _, pv, house in series:
        pv *= a.pv_factor
        direct = min(pv, house, a.limit)
        surplus = pv - direct
        charge = min(surplus + direct * a.charge_first, max(hi - soc, 0) / a.efficiency)
        direct -= max(charge - surplus, 0)
        surplus -= min(charge, surplus)
        soc += charge * a.efficiency
        export = min(surplus, a.limit - direct)
        # in einer Stunde mit Ladung entlädt der Speicher nicht, die Lücke deckt das Netz (so misst es sich beim EZHI)
        discharge = 0.0 if charge else max(min(min(house, a.limit) - direct, (soc - lo) * a.efficiency), 0.0)
        soc -= discharge / a.efficiency
        standby = a.standby if direct + discharge + export == 0 else 0.0
        tot["netzbezug"] += house - direct - discharge + standby
        tot["einspeisung"] += export
        tot["ins_haus"] += direct + discharge - standby
        tot["geladen"] += charge
        tot["entladen"] += discharge
        tot["abgeregelt"] += surplus - export
    return {k: v / 1000 for k, v in tot.items()}


def measured(rows, start, end):
    """Gemessene Summen im gleichen Zeitraum und Format wie simulate(), als Prüfstein."""
    valid = {h for h, *_ in hours(rows, start, end)}
    tot = dict.fromkeys(("netzbezug", "einspeisung", "ins_haus", "geladen", "entladen"), 0.0)
    for key, hour, mean, pos, neg, *_ in rows:
        if hour not in valid:
            continue
        if key == "grid_power":
            tot["netzbezug"] += pos
            tot["einspeisung"] -= neg
        elif key == "output_power":
            tot["ins_haus"] += pos + neg  # Bezug des Wechselrichters zieht von der Abgabe ab
        elif key == "battery_power":
            tot["geladen"] += pos
            tot["entladen"] -= neg
    return {k: v / 1000 for k, v in tot.items()}


def calibrate(series, anlage, charged, soc0=None):
    """Ladevorrang, bei dem die Simulation so viel lädt wie gemessen (charged in kWh); 0 ohne Akku oder Ladung.
    Vereinfachung: Suche in 5-%-Schritten, genauer geben Stundenwerte ohnehin nicht her."""
    if not anlage.capacity or not charged:
        return 0.0
    return min((k / 20 for k in range(20)), key=lambda share: abs(
        simulate(series, replace(anlage, charge_first=share), soc0)["geladen"] - charged))
