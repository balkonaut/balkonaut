"""Auswertung aus den Stundenwerten: Energiebilanz, Ersparnis und Amortisation.

Begriffe und Formeln: docs/auswertung.md
"""
import statistics
from collections import defaultdict
import calendar
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")  # ponytail: feste Zeitzone, konfigurierbar machen für Nutzer außerhalb DE/AT
MAX_KWH_PER_DAY = 1.2 * 24  # ponytail: Höchstwert EZHI (1200 W), fängt nur grobe Datumsfehler; Limit aus HA lesen, falls nötig


def _years_since(rows, commissioned):
    """Jahre von der Inbetriebnahme (date) bis zur letzten Stunde in rows, None ohne Datum oder Daten."""
    if not commissioned or not rows:
        return None
    end = max(h for _, h, *_ in rows) + 3600
    years = (end - datetime.combine(commissioned, time(), TZ).timestamp()) / (365.25 * 86400)
    return years if years > 0 else None


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


def expected_share(start, end, profile):
    """Anteil des erwarteten Jahresertrags (profile: kWh je Monat) im Zeitraum [start, end) als Jahresbruchteil."""
    day, last, energy = datetime.fromtimestamp(start, TZ).date(), datetime.fromtimestamp(end, TZ).date(), 0.0
    while day < last:
        energy += profile[day.month - 1] / calendar.monthrange(day.year, day.month)[1]
        day += timedelta(days=1)
    return energy / sum(profile)


def amortization(rows, prices, cost, commissioned=None, profile=None):
    """Bisherige Ersparnis und Restlaufzeit bis zur Amortisation.

    Bisherige Ersparnis: Stand des Abgabezählers mal gemessener Eigenverbrauchsquote mal Arbeitspreis;
    ohne Zähler nur der Messzeitraum. Ersparnis pro Jahr: mit Datum der Inbetriebnahme (Start des
    Abgabezählers) der Durchschnitt seitdem, sonst der Messzeitraum. Mit Ertragsprofil (kWh je Monat)
    wird der Zeitraum nach seinem erwarteten Anteil am Jahresertrag hochgerechnet statt nach Tagen.
    """
    total = balance(rows, 0, prices)
    hours = [h for _, h, *_ in rows]
    days = (max(hours) - min(hours) + 3600) / 86400 if hours else 0
    meter = [last for key, _, _, _, _, last in rows if key == "output_energy" and last is not None]
    if meter and total["eigenverbrauchsquote"] is not None:
        saved = meter[-1] * total["eigenverbrauchsquote"] * prices["energy"]
    else:
        saved = total["ersparnis"]
    years = _years_since(rows, commissioned)
    end = max(hours) + 3600 if hours else 0
    if years and meter:
        basis, amount, start = "inbetriebnahme", saved, end - years * 365.25 * 86400
    else:
        basis, amount, start = "messtage", total["ersparnis"], min(hours) if hours else 0
    if profile and hours:
        share = expected_share(start, end, profile)
        per_year = amount / share if share else 0.0
    else:  # ohne Profil: gleichmäßig über das Jahr verteilt
        per_year = amount / ((end - start) / (365.25 * 86400)) if end > start else 0.0
    remaining = max(cost - saved, 0.0)
    years_left = remaining / per_year if per_year else None
    return {
        "kosten": cost,
        "bisher_gespart": saved,
        "ersparnis_pro_jahr": per_year,
        "basis": basis,
        "jahresverlauf": bool(profile),
        "erwarteter_ertrag_jahr": sum(profile) if profile else None,
        "rest": remaining,
        "jahre_bis_amortisation": years_left,
        "amortisiert_am": (datetime.fromtimestamp(max(hours) + 3600, TZ) + timedelta(days=years_left * 365.25)).date()
        if years_left is not None and hours else None,
        "zaehler_plausibel": not (years and meter) or meter[-1] / (years * 365.25) <= MAX_KWH_PER_DAY,
        "messtage": days,
    }


def battery(rows, start, prices, commissioned=None):
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
        "zyklen_pro_jahr": latest("battery_discharge_energy") / cap / years
        if cap and latest("battery_discharge_energy") and (years := _years_since(rows, commissioned)) else None,
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


NEAR_ZERO = 50  # W, Band um 0 W, das als ausgeregelt gilt
JUMP = 300  # W, Anstieg der Netzleistung zwischen zwei Messungen, der als Lastsprung zählt


def regulation(series, prices, soc_min=10, limit=800):
    """Regelgüte der Nulleinspeisung aus Rohwerten {ts: {grid_power, output_power, pv_ac_power, battery_soc}}.

    Nachregeln kann der Speicher nur, wenn der Akku über der Untergrenze ist und sein eigener Anteil an
    der Abgabe (Abgabe minus durchgereichte AC-Erzeugung, z. B. EZ1-M) unter seinem Limit liegt.
    """
    pts = [(ts, v["grid_power"], v.get("output_power"), v.get("pv_ac_power") or 0, v.get("battery_soc"))
           for ts, v in sorted(series.items()) if v.get("grid_power") is not None]
    if not pts:
        return None
    step = 10  # Messraster des Collectors in s
    kwh = step / 3600 / 1000

    def headroom(o, ac, soc):
        if o is None or soc is None or soc <= soc_min + 2:
            return 0
        return max(limit - (o - ac), 0) if o - ac < limit * 0.95 else 0

    grids, export, avoidable, jumps = [], 0.0, 0.0, []
    for i, (ts, g, o, ac, soc) in enumerate(pts):
        export += max(-g, 0) * kwh
        room = headroom(o, ac, soc)
        if not room:
            continue
        grids.append(g)
        avoidable += min(max(g, 0), room) * kwh
        if i and g - pts[i - 1][1] > JUMP:  # Lastsprung: Zeit bis zurück im Band, höchstens 5 min
            jumps.append(next((t2 - ts for t2, g2, *_ in pts[i + 1:i + 31] if g2 <= NEAR_ZERO), None))
    done = [s for s in jumps if s is not None]
    outputs = [o for _, _, o, _, _ in pts if o is not None]
    return {
        "zeitraum_stunden": len(pts) * step / 3600,
        "regelbereit_stunden": len(grids) * step / 3600,
        "anteil_nahe_null": sum(abs(g) <= NEAR_ZERO for g in grids) / len(grids) if grids else None,
        "median_netz": statistics.median(grids) if grids else None,
        "vermeidbarer_netzbezug": avoidable,
        "vermeidbare_kosten": avoidable * prices["energy"],
        "einspeisung": export,
        "einspeisung_wert": export * (prices["energy"] - prices["feed_in"]),
        "lastspruenge": len(jumps),
        "reaktionszeit_median": statistics.median(done) if done else None,
        "nicht_ausgeregelt": len(jumps) - len(done),
        "limit": limit,
        "max_abgabe": max(outputs, default=None),
        "anteil_ueber_limit": sum(o > limit for o in outputs) / len(outputs) if outputs else None,
    }


WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]


def _ts(d):
    return datetime.combine(d, time(), TZ).timestamp()


def buckets(view, d):
    """Balken einer Verlaufsansicht: (Titel, [(Beschriftung, start, ende)], vorheriges Datum, nächstes Datum)."""
    if view == "woche":
        mon = d - timedelta(days=d.weekday())
        days = [mon + timedelta(days=i) for i in range(7)]
        iso = mon.isocalendar()
        bars = [(f"{WEEKDAYS[x.weekday()]} {x.day}.", _ts(x), _ts(x + timedelta(days=1))) for x in days]
        return f"KW {iso.week}/{iso.year}", bars, mon - timedelta(days=7), mon + timedelta(days=7)
    if view == "monat":
        first = d.replace(day=1)
        nxt = (first + timedelta(days=32)).replace(day=1)
        days = [first + timedelta(days=i) for i in range((nxt - first).days)]
        bars = [(str(x.day), _ts(x), _ts(x + timedelta(days=1))) for x in days]
        return f"{MONTHS[first.month - 1]} {first.year}", bars, (first - timedelta(days=1)).replace(day=1), nxt
    if view == "jahr":
        firsts = [date(d.year, m, 1) for m in range(1, 13)] + [date(d.year + 1, 1, 1)]
        bars = [(MONTHS[a.month - 1][:3], _ts(a), _ts(b)) for a, b in zip(firsts, firsts[1:])]
        return str(d.year), bars, date(d.year - 1, 1, 1), date(d.year + 1, 1, 1)
    start, end = int(_ts(d)), int(_ts(d + timedelta(days=1)))  # Tag, Stunden in Ortszeit (23/25 bei Zeitumstellung)
    edges = list(range(start, end, 3600)) + [end]
    bars = [(datetime.fromtimestamp(a, TZ).strftime("%H"), a, b) for a, b in zip(edges, edges[1:])]
    return f"{WEEKDAYS[d.weekday()]}, {d:%d.%m.%Y}", bars, d - timedelta(days=1), d + timedelta(days=1)


def history(rows, bars, prices):
    """Bilanz je Balken: Eigenverbrauch, Netzbezug und Erzeugung in kWh."""
    # ponytail: rechnet jeden Balken einzeln (Jahr: 12 Durchläufe über ein Jahr Stundenwerte); bei Bedarf vorsummieren
    lo = bars[0][1] - 7 * 86400  # Zähler brauchen einen Basiswert vor dem ersten Balken
    rows = [r for r in rows if lo <= r[1] < bars[-1][2]]
    out = []
    for label, a, b in bars:
        x = balance([r for r in rows if r[1] < b], a, prices)
        out.append({"label": label, "own": x["eigenverbrauch"], "grid": x["netzbezug"], "gen": x["erzeugung"]})
    return out


LOW = 0.6  # Ertrag unter 60 % der Prognose gilt als niedrig
UNEVEN = 0.7  # ein Wechselrichter erreicht weniger als 70 % der Prognosetreue des anderen
INVERTERS = {  # Name: (Erzeugung als Zähler, als Leistung, Prognose für heute)
    "speicher": ("pv_energy", "pv_power", "pv_forecast_today"),
    "ac": ("", "pv_ac_power", "pv_ac_forecast_today"),
}


def yield_watch(rows, now, days=7):
    """Ertrag je Wechselrichter gegen die Tagesprognose seiner Fläche über die letzten vollen Tage.

    Die Prognose eines Tages ist der Mittelwert des Sensors „Erzeugung heute“ über die Stunden des Tages.
    """
    # ponytail: ein voller Akku regelt die PV am Speicher ab und senkt dessen Ertrag; Tage mit vollem Akku ausklammern, falls das stört
    end = periods(now)["tag"]
    start = datetime.combine(datetime.fromtimestamp(end, TZ).date() - timedelta(days=days), time(), TZ).timestamp()
    wh, counter, hours, energy = _collect([r for r in rows if r[1] < end], start)
    result, warnings = {}, []
    for name, (counter_key, power_key, forecast_key) in INVERTERS.items():
        by_day = defaultdict(list)
        for hour, (mean, *_) in hours.get(forecast_key, {}).items():
            by_day[datetime.fromtimestamp(hour, TZ).date()].append(mean)
        forecast = sum(sum(v) / len(v) for v in by_day.values())
        actual = counter[counter_key] if counter_key in counter else wh[power_key] / 1000
        result[name] = {"ertrag": actual, "prognose": forecast, "tage": len(by_day),
                        "quote": actual / forecast if forecast >= 1 else None}
    label = {"speicher": "Speicher-Wechselrichter", "ac": "zweiter Wechselrichter"}
    for name, r in result.items():
        if r["quote"] is not None and r["tage"] >= 3 and r["quote"] < LOW:
            warnings.append({"code": "ertrag_niedrig", "wechselrichter": name,
                             "text": f"{label[name]}: {r['quote']:.0%} der Prognose in den letzten {r['tage']} Tagen"})
    q = [r["quote"] for r in result.values() if r["quote"] and r["tage"] >= 3]
    if len(q) == 2 and min(q) / max(q) < UNEVEN:
        weak = min(result, key=lambda n: result[n]["quote"] or 0)
        warnings.append({"code": "ungleich", "wechselrichter": weak,
                         "text": f"{label[weak]} bleibt deutlich hinter dem anderen zurück (Verschattung, Verschmutzung, Defekt?)"})
    return {"wechselrichter": result, "warnungen": warnings}
