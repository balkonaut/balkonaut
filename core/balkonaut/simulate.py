"""Simulator: Energiefluss Stunde für Stunde aus gemessenem Hausverbrauch und PV-Erzeugung nachrechnen.

Grundlage sind die Stundenwerte (Mittelwert in W = Wh je Stunde). Hausverbrauch = Abgabe + Netz, PV = beide
Wechselrichter. Modell der Nulleinspeisung: PV deckt das Haus bis zum Abgabelimit, Überschuss lädt den Akku, der Rest
geht bis zum Limit ins Netz, darüber wird abgeregelt; fehlt Leistung, entlädt der Akku bis zur Untergrenze.
Ladevorrang: Manche Speicher (EZHI) laden auch dann, wenn das Haus den Strom gerade selbst bräuchte; dieser Anteil wird
aus der Messung bestimmt (calibrate), sonst trifft die Simulation zwar den Netzbezug, aber nicht die Akku-Zyklen.
Vereinfachung: Stundenmittel, Lastspitzen innerhalb einer Stunde sieht das Modell nicht; genauer ginge es nur mit den
Rohwerten, die nach 14 Tagen gelöscht werden.
"""
import calendar
import math
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

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
    base_load: float | None = None  # W fest abgeben statt Nulleinspeisung (None = dem Hausverbrauch folgen)


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
        target = min(house if a.base_load is None else a.base_load, a.limit)
        direct = min(pv, target)
        surplus = pv - direct
        charge = min(surplus + direct * a.charge_first, max(hi - soc, 0) / a.efficiency)
        direct -= max(charge - surplus, 0)
        surplus -= min(charge, surplus)
        soc += charge * a.efficiency
        export = min(surplus, a.limit - direct)
        # in einer Stunde mit Ladung entlädt der Speicher nicht, die Lücke deckt das Netz (so misst es sich beim EZHI)
        discharge = 0.0 if charge else max(min(target - direct, (soc - lo) * a.efficiency), 0.0)
        soc -= discharge / a.efficiency
        out = direct + discharge + export
        to_house = min(out, house)  # bei fester Grundlast geht, was das Haus nicht braucht, ins Netz
        standby = a.standby if out == 0 else 0.0
        tot["netzbezug"] += house - to_house + standby
        tot["einspeisung"] += out - to_house
        tot["ins_haus"] += to_house - standby
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


def days(series, tz):
    """Vollständige Tage aus der Stundenreihe: [(Datum, PV[24], Haus[24])], nach Ortszeit (Sommerzeit-Tage fallen weg)."""
    by = {}
    for hour, pv, house in series:
        t = datetime.fromtimestamp(hour, tz)
        by.setdefault(t.date(), {})[t.hour] = (pv, house)
    return [(day, [v[h][0] for h in range(24)], [v[h][1] for h in range(24)])
            for day, v in sorted(by.items()) if len(v) == 24]


def _sun(day, lat, lon, offset):
    """Anteile der Tageserzeugung je Ortsstunde: Sinusbogen zwischen Sonnenauf- und -untergang.
    Vereinfachung: ohne Ausrichtung der Flächen und ohne Wolken im Tagesverlauf."""
    decl = math.radians(23.44) * math.sin(2 * math.pi * (284 + day.timetuple().tm_yday) / 365)
    half = math.degrees(math.acos(max(-1.0, min(1.0, -math.tan(math.radians(lat)) * math.tan(decl))))) / 15
    noon = 12 - lon / 15 + offset
    w = [max(math.sin(math.pi * (h + 0.5 - noon + half) / (2 * half)), 0) if abs(h + 0.5 - noon) < half else 0.0
         for h in range(24)]
    return [x / sum(w) for x in w] if sum(w) else w


def year(measured_days, profile, lat, lon, tz, start=date(2025, 1, 1)):
    """Ein Jahr Stundenreihe: Hausverbrauch der gemessenen Tage der Reihe nach wiederholt (ohne Jahreszeiten),
    PV je Monat aus profile (kWh, z. B. PVGIS), je Tag so schwankend wie an den gemessenen Tagen."""
    mean = sum(sum(pv) for _, pv, _ in measured_days) / len(measured_days)
    out = []
    for i in range(365):
        day = start + timedelta(days=i)
        _, pv, house = measured_days[i % len(measured_days)]
        weather = sum(pv) / mean if mean else 1.0
        energy = profile[day.month - 1] * 1000 / calendar.monthrange(day.year, day.month)[1] * weather
        t0 = int(datetime(day.year, day.month, day.day, tzinfo=tz).timestamp())
        offset = datetime(day.year, day.month, day.day, 12, tzinfo=tz).utcoffset().total_seconds() / 3600
        out += [(t0 + h * 3600, energy * s, house[h]) for h, s in enumerate(_sun(day, lat, lon, offset))]
    return out


def euro(r, prices):
    """Ersparnis in € aus Summen von simulate(): vermiedener Netzbezug plus Vergütung der Einspeisung."""
    return r["ins_haus"] * prices["energy"] + r["einspeisung"] * prices.get("feed_in", 0)


def compare(series, anlage, variant, prices, variant_prices=None, factor=1.0):
    """Heutige Anlage gegen Variante (anderer Akku, Module, Limit, Regelung, Tarif): Summen und Ersparnis je Seite,
    mit factor aufs Jahr hochgerechnet, dazu die Mehrersparnis der Variante."""
    out = {}
    for name, a, p in (("heute", anlage, prices), ("variante", variant, variant_prices or prices)):
        r = {k: v * factor for k, v in simulate(series, a).items()}
        out[name] = {**r, "ersparnis": euro(r, p)}
    out["mehr"] = out["variante"]["ersparnis"] - out["heute"]["ersparnis"]
    return out
