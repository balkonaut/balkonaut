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


def _recent(rows, start, end=float("inf")):
    """Zeilen von start bis end, dazu eine Woche davor: Zähler brauchen einen Basiswert vor start."""
    return [r for r in rows if start - 7 * 86400 <= r[1] < end]


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


def balance(rows, start, prices, collected=None):
    """rows: (key, hour, mean, mean_pos, mean_neg, last), sortiert nach key und hour. Energie in kWh.
    collected: Ergebnis von _collect(rows, start), wenn schon vorhanden."""
    wh, counter, hours, energy = collected or _collect(rows, start)
    grid_import, grid_export = wh["grid_power+"] / 1000, wh["grid_power-"] / 1000
    output = energy("output_energy", "output_power+")
    self_use = max(output - grid_export, 0.0)
    consumption = grid_import + self_use
    return {
        # nur positive Anteile: ein Verbraucher am Off-Grid-Port (oder Standby) ist keine negative Erzeugung
        "erzeugung": energy("pv_energy", "pv_power+") + wh["pv_ac_power+"] / 1000,
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


def amortization(rows, prices, cost, commissioned=None, profile=None, total=None):
    """Bisherige Ersparnis und Restlaufzeit bis zur Amortisation.

    Bisherige Ersparnis: Stand des Abgabezählers mal gemessener Eigenverbrauchsquote mal Arbeitspreis;
    ohne Zähler nur der Messzeitraum. Ersparnis pro Jahr: mit Datum der Inbetriebnahme (Start des
    Abgabezählers) der Durchschnitt seitdem, sonst der Messzeitraum. Mit Ertragsprofil (kWh je Monat)
    wird der Zeitraum nach seinem erwarteten Anteil am Jahresertrag hochgerechnet statt nach Tagen.
    """
    total = total or balance(rows, 0, prices)  # total: Bilanz gesamt, wenn schon berechnet
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
        "rest": remaining,
        "jahre_bis_amortisation": years_left,
        "amortisiert_am": (datetime.fromtimestamp(max(hours) + 3600, TZ) + timedelta(days=years_left * 365.25)).date()
        if years_left is not None and years_left <= 100 and hours else None,  # sonst kein sinnvolles Datum
        "zaehler_plausibel": not (years and meter) or meter[-1] / (years * 365.25) <= MAX_KWH_PER_DAY,
        "messtage": days,
    }


def _known(rows):
    """Letzte bekannte Kapazität und Ladegrenzen aus allen Stundenwerten, auch vor dem Zeitraum: Geräte melden sie
    selten oder nur über die Cloud (EZHI-Grenzen), dann fehlen sie im Zeitraum."""
    return {k: last for k, _, _, _, _, last in rows if k in ("battery_capacity", "battery_soc_max", "battery_soc_min")
            and last is not None}


def battery(rows, start, prices, commissioned=None, collected=None, known=None):
    """Akku-Auswertung ab start: Zyklen, Gesundheit, Wirkungsgrad, Zeiten mit vollem/leerem Akku.
    known: Ergebnis von _known(alle Stundenwerte), wenn schon vorhanden."""
    wh, counter, hours, energy = collected or _collect(rows, start)
    known = _known(rows) if known is None else known

    def first(key):
        return hours[key][min(hours[key])][3] if hours.get(key) else None

    def latest(key):
        return hours[key][max(hours[key])][3] if hours.get(key) else None

    cap = latest("battery_capacity") or known.get("battery_capacity")
    charge, discharge = counter.get("battery_charge_energy"), counter.get("battery_discharge_energy")
    # Ladestand zu Beginn: letzter Wert vor dem Zeitraum, denn die Zähler zählen ab dessen Beginn
    before = [last for key, hour, _, _, _, last in rows if key == "battery_soc" and hour < start and last is not None]
    soc0, soc1 = before[-1] if before else first("battery_soc"), latest("battery_soc")
    efficiency = None
    if cap and charge and charge > 0.5 and discharge is not None and None not in (soc0, soc1):
        efficiency = (discharge + (soc1 - soc0) / 100 * cap) / charge
        if efficiency > 1:  # Ladestand nur auf 1 bis 2 % genau: über 100 % ist Messungenauigkeit, kein Wert
            efficiency = None
    inputs = energy("pv_energy", "pv_power") + (wh["pv_ac_power"] + wh["output_power-"]) / 1000 + (discharge or 0)
    outputs = energy("output_energy", "output_power+") + (charge or 0)

    # Wege der Energie: aus dem Akku ins Haus je Stunde höchstens der Eigenverbrauch dieser Stunde, der Rest der
    # Entladung sind Wandlungsverluste oder ging ins Netz. ponytail: in Stunden mit Sonne und Entladung zählt der Akku
    # zuerst, genauer ginge es nur mit Messwerten im Sekundentakt.
    self_use = max(energy("output_energy", "output_power+") - wh["grid_power-"] / 1000, 0.0)
    to_house = None
    if "battery_power" in hours and "output_power" in hours:
        to_house = sum(min(-neg, max(hours["output_power"].get(h, (0, 0))[1] + hours["grid_power"].get(h, (0, 0, 0))[2], 0))
                       for h, (_, _, neg, _) in hours["battery_power"].items()) / 1000

    soc_max = latest("battery_soc_max") or known.get("battery_soc_max") or 100
    soc_min = latest("battery_soc_min") or known.get("battery_soc_min") or 0
    full = empty = 0
    export_full = import_empty = 0.0
    # Größerer Akku: Nach Stunden mit vollem Akku hätte ein zusätzliches Modul (halbe Kapazität, nutzbar zwischen den
    # Grenzen, 90 % Wirkungsgrad) den Netzbezug der folgenden leeren Stunden bis zu seinem Inhalt decken können.
    # ponytail: nur Obergrenze, der abgeregelte Überschuss ist nicht gemessen; genau rechnet später der Simulator.
    extra = cap / 2 if cap else None
    usable = extra * (soc_max - soc_min) / 100 * 0.9 if extra else 0.0
    shifted = left = 0.0
    for hour, (soc, *_) in hours.get("battery_soc", {}).items():
        _, pos, neg, _ = hours["grid_power"].get(hour, (0, 0, 0, None))
        if soc >= soc_max - 2:
            full += 1
            export_full -= neg / 1000
            left = usable
        elif soc <= soc_min + 2:
            empty += 1
            import_empty += pos / 1000
            take = min(pos / 1000, left)
            shifted, left = shifted + take, left - take
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
        "zusatz_kapazitaet": extra,
        "groesserer_akku": shifted if extra else None,
        # aufs Jahr hochgerechnet über die Stunden mit Ladestand; ponytail: linear, ohne Jahreszeiten
        "groesserer_akku_jahr": shifted * prices["energy"] * 8760 / len(hours["battery_soc"])
        if extra and hours.get("battery_soc") else None,
        "geladen": charge if charge is not None else wh["battery_power+"] / 1000,
        "entladen": discharge if discharge is not None else wh["battery_power-"] / 1000,
        "entladen_ins_haus": to_house,
        "direkt_ins_haus": None if to_house is None else max(self_use - to_house, 0.0),
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
    hours = [[0, 0, 0.0] for _ in range(24)]  # je Uhrzeit (Ortszeit): regelbereite Messungen, davon nahe 0, vermeidbar
    for i, (ts, g, o, ac, soc) in enumerate(pts):
        export += max(-g, 0) * kwh
        room = headroom(o, ac, soc)
        if not room:
            continue
        grids.append(g)
        avoidable += min(max(g, 0), room) * kwh
        h = hours[datetime.fromtimestamp(ts, TZ).hour]
        h[0] += 1
        h[1] += abs(g) <= NEAR_ZERO
        h[2] += min(max(g, 0), room) * kwh
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
        "stunden": [{"stunde": i, "regelbereit_stunden": n * step / 3600, "anteil_nahe_null": near / n if n else None,
                     "vermeidbarer_netzbezug": avoid} for i, (n, near, avoid) in enumerate(hours)],
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


def history(rows, bars, prices, forecast=None):
    """Bilanz je Balken: Eigenverbrauch, Netzbezug und Erzeugung in kWh; mit forecast ({Stundenbeginn: kWh}, nur für
    Stundenbalken) dazu die erwartete Erzeugung."""
    # ponytail: rechnet jeden Balken einzeln (Jahr: 12 Durchläufe über ein Jahr Stundenwerte); bei Bedarf vorsummieren
    rows = _recent(rows, bars[0][1], bars[-1][2])
    out = []
    for label, a, b in bars:
        x = balance([r for r in rows if r[1] < b], a, prices)
        out.append({"label": label, "own": x["eigenverbrauch"], "grid": x["netzbezug"], "gen": x["erzeugung"],
                    "fc": forecast.get(a) if forecast else None, "datum": datetime.fromtimestamp(a, TZ).date().isoformat()})
    return out


LOW = 0.6  # Ertrag unter 60 % der Prognose gilt als niedrig
UNEVEN = 0.7  # ein Wechselrichter erreicht weniger als 70 % der Prognosetreue des anderen
INVERTERS = {  # Name: (Erzeugung als Zähler, als Leistung, Prognose für heute)
    "speicher": ("pv_energy", "pv_power", "pv_forecast_today"),
    "ac": ("", "pv_ac_power", "pv_ac_forecast_today"),
}


def yield_watch(rows, now):
    """Ertrag je Wechselrichter gegen die Tagesprognose seiner Fläche über die letzten vollen Tage.

    Die Prognose eines Tages ist der Mittelwert des Sensors „Erzeugung heute“ über die Stunden des Tages.
    """
    # ponytail: ein voller Akku regelt die PV am Speicher ab und senkt dessen Ertrag; Tage mit vollem Akku ausklammern, falls das stört
    end = periods(now)["tag"]
    start = datetime.combine(datetime.fromtimestamp(end, TZ).date() - timedelta(days=7), time(), TZ).timestamp()
    rows = _recent(rows, start, end)  # nur die letzten 7 Tage, nicht für jeden Tag die ganze Historie
    hours = _collect(rows, start)[2]
    result, warnings = {}, []
    for name, (counter_key, power_key, forecast_key) in INVERTERS.items():
        by_day = defaultdict(list)
        for hour, (mean, *_) in hours.get(forecast_key, {}).items():
            by_day[datetime.fromtimestamp(hour, TZ).date()].append(mean)
        forecast = sum(sum(v) / len(v) for v in by_day.values())
        actual = 0.0  # nur Tage mit Prognose vergleichen, sonst verzerrt eine junge Prognose die Quote
        for day in by_day:
            day_end = _ts(day + timedelta(days=1))  # Ortszeit: 23 oder 25 Stunden bei Zeitumstellung
            w, c, _, _ = _collect([r for r in rows if r[1] < day_end], _ts(day))
            actual += c[counter_key] if counter_key in c else w[power_key + "+"] / 1000
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


def month_report(rows, d, prices, commissioned=None):
    """Monatsbericht für den Monat von d: Bilanz im Vergleich zu Vormonat und Vorjahresmonat, Akku und Tageswerte."""
    def bounds(day):
        bars = buckets("monat", day)[1]
        return bars[0][1], bars[-1][2], bars

    def bal(start, end):
        return balance([r for r in rows if r[1] < end], start, prices)

    first = d.replace(day=1)
    start, end, bars = bounds(first)
    prev = (first - timedelta(days=1)).replace(day=1)
    last_year = first.replace(year=first.year - 1)
    return {
        "monat": f"{MONTHS[first.month - 1]} {first.year}",
        "zurueck": prev, "weiter": (first + timedelta(days=32)).replace(day=1),
        "bilanz": bal(start, end), "vormonat": bal(*bounds(prev)[:2]), "vorjahr": bal(*bounds(last_year)[:2]),
        "akku": battery([r for r in rows if r[1] < end], start, prices, commissioned),
        "tage": history(rows, bars, prices),
    }


def combine_regulation(days):
    """Tageswerte der Regelgüte zu einem Zeitraum zusammenfassen; Anteile und Mediane nach Stunden gewichtet."""
    days = [d for d in days if d]
    if not days:
        return None
    hours = sum(d["zeitraum_stunden"] for d in days)
    ready = sum(d["regelbereit_stunden"] for d in days)

    def weighted(key, weight):
        pairs = [(d[key], d[weight]) for d in days if d[key] is not None and d[weight]]
        total = sum(w for _, w in pairs)
        return sum(v * w for v, w in pairs) / total if total else None

    out = {k: sum(d[k] for d in days) for k in ("vermeidbarer_netzbezug", "vermeidbare_kosten", "einspeisung",
                                                  "einspeisung_wert", "lastspruenge", "nicht_ausgeregelt")}
    reactions = [d["reaktionszeit_median"] for d in days if d["reaktionszeit_median"] is not None]
    out.update(zeitraum_stunden=hours, regelbereit_stunden=ready,
               anteil_nahe_null=weighted("anteil_nahe_null", "regelbereit_stunden"),
               median_netz=weighted("median_netz", "regelbereit_stunden"),  # Näherung: gewichtetes Mittel der Tagesmediane
               reaktionszeit_median=statistics.median(reactions) if reactions else None,
               limit=max(d["limit"] for d in days),
               max_abgabe=max((d["max_abgabe"] for d in days if d["max_abgabe"] is not None), default=None),
               anteil_ueber_limit=weighted("anteil_ueber_limit", "zeitraum_stunden"), tage=len(days))
    return out


def status(rows, latest, now, prices, cost, commissioned=None, profile=None):
    """Gesamtstand wie /api/v1/status: Warnungen, Ertrag, letzte Messwerte, Bilanz und Akku für heute, Monat,
    Jahr und gesamt sowie Amortisation. rows: Stundenwerte, latest: {Messgröße: (ts, wert)}."""
    recent = {name: (r := _recent(rows, start), start, _collect(r, start)) for name, start in periods(now).items()}
    bilanz = {name: balance(r, start, prices, c) for name, (r, start, c) in recent.items()}
    known = _known(rows)
    watch = yield_watch(rows, now)
    warnings = watch["warnungen"]
    # Prognosen kommen auch, wenn alle Geräte ausfallen, und zählen deshalb nicht als Messwert
    stand = max((ts for key, (ts, _) in latest.items() if not key.endswith("_forecast_today")), default=None)
    if stand is not None and now - stand > 120:
        warnings = [{"code": "keine_messwerte",
                     "text": "Seit über 2 Minuten keine Messwerte, Verbindung zu den Geräten bzw. Home Assistant prüfen"}] + warnings
    return {
        "warnungen": warnings,
        "ertrag": watch["wechselrichter"],
        "stand": datetime.fromtimestamp(stand, TZ) if stand is not None else None,
        "live": {k: v for k, (_, v) in latest.items()},
        "bilanz": bilanz,
        "akku": {name: battery(r, start, prices, commissioned, c, known) for name, (r, start, c) in recent.items()},
        "amortisation": amortization(rows, prices, cost, commissioned, profile, bilanz["gesamt"]),
    }
