"""Auswertungen für die Ansichten Verlauf, Bericht und Nulleinspeisung, gemeinsam für Docker-App und Integration.

storage: balkonaut.storage.Storage, now: Unix-Zeit, prices: {"energy", "feed_in"} in €/kWh.
"""
from datetime import date, datetime, timedelta

from . import analytics
from .storage import RAW_DAYS

VIEWS = {"tag": "Tag", "woche": "Woche", "monat": "Monat", "jahr": "Jahr"}
REGULATION_KEYS = ["grid_power", "output_power", "pv_ac_power", "battery_soc"]


# Erklärung und Bewertung je Kachel, für Docker-App und Panel: (Erklärung, gut, schlecht, Text gut, Text schlecht).
# gut/schlecht None: keine Bewertung. Höher ist besser, wenn gut > schlecht. Werte in den Einheiten der Auswertung
# (Anteile 0 bis 1). Vereinfachung: feste Grenzen für alle Anlagen, je Anlage einstellbar machen, falls nötig.
KACHELN = {
    "bilanz": {
        "ersparnis": ("Eigenverbrauch mal Arbeitspreis plus Einspeisung mal Vergütung.",),
        "eigenverbrauch": ("Strom des Balkonkraftwerks, der im Haus verbraucht wurde: Abgabe minus Einspeisung.",),
        "autarkiegrad": ("Anteil des Hausverbrauchs, den das Balkonkraftwerk gedeckt hat. Bei Balkonkraftwerken sind "
                         "30 bis 40 % schon viel, deshalb ohne Bewertung.",),
        "eigenverbrauchsquote": ("Anteil der Abgabe ins Haus, der selbst verbraucht und nicht eingespeist wurde. "
                                 "Je höher, desto besser.", 0.9, 0.6, "≥ 90 %", "≤ 60 %"),
        "erzeugung": ("Was die Module erzeugt haben, bei mehreren Wechselrichtern zusammen.",),
        "hausverbrauch": ("Gesamter Verbrauch im Haus: Abgabe des Balkonkraftwerks plus Netzbezug.",),
        "netzbezug": ("Strom aus dem Netz laut Zähler am Hausanschluss.",),
        "einspeisung": ("Strom, der ins Netz ging, laut Zähler am Hausanschluss.",),
    },
    "akku": {
        "zyklen": ("Entladene Energie geteilt durch die nutzbare Kapazität. Gesamt zählt seit Inbetriebnahme des Speichers.",),
        "gesundheit": ("Vom Speicher gemeldeter Zustand in % der ursprünglichen Kapazität.",),
        "wirkungsgrad": ("Entladene Energie plus Änderung des Ladestands, geteilt durch geladene Energie. Erst ab etwa "
                         "0,5 kWh Ladung aussagekräftig.", 0.9, 0.75, "≥ 90 %", "≤ 75 %"),
        "verluste_wechselrichter": ("Anteil der Energie, die im Speicher-Wechselrichter verloren geht. Je kleiner, desto "
                                    "besser.", 0.05, 0.15, "≤ 5 %", "≥ 15 %"),
        "stunden_voll": ("Stunden mit Ladestand nahe der Obergrenze. Überschuss wird dann meist abgeregelt, ein größerer "
                         "Akku könnte ihn speichern.",),
        "stunden_leer": ("Stunden mit Ladestand nahe der Untergrenze. Der Netzbezug dabei ist die Obergrenze dessen, was "
                         "ein größerer Akku hätte abdecken können.",),
        "groesserer_akku": ("Was ein zusätzliches Akku-Modul (halbe heutige Kapazität) höchstens gebracht hätte: Netzbezug "
                            "in Stunden mit leerem Akku, nachdem er vorher voll war, bis zum nutzbaren Inhalt des Moduls, "
                            "aufs Jahr hochgerechnet. Obergrenze, weil der abgeregelte Überschuss nicht gemessen wird. Im "
                            "Herbst und Winter fast immer „lohnt nicht“, aussagekräftig erst über Frühjahr und Sommer.",
                            100, 30, "≥ 100 € im Jahr", "≤ 30 € im Jahr", ("lohnt sich", "eher nicht", "lohnt nicht")),
    },
    "diagramm": {
        "herkunft": ("Je Zeitabschnitt zwei Balken: grün, was das Balkonkraftwerk ins Haus abgegeben hat (direkt von der "
                     "Sonne oder aus dem Akku), blau, was aus dem Netz kam; zusammen der Hausverbrauch. Der gelbe Strich "
                     "ist die Erzeugung aller Module, egal wohin sie ging: Liegt er über Grün, ging der Rest in den Akku "
                     "oder ins Netz; liegt er darunter, half der Akku aus. Die gestrichelte Linie ist die erwartete "
                     "Erzeugung laut Forecast.Solar, nur für heute.",),
        "uhrzeit": ("Die letzten 7 Tage nach Uhrzeit zusammengefasst. Oben je Stunde der Anteil der regelbereiten Zeit, "
                    "in der der Netzanschluss bei ±50 W lag, in %: grün ab 80 %, rot bis 50 %. Blasse Felder ohne Zahl: "
                    "In dieser Stunde konnte der Speicher nie nachregeln (Akku leer oder Abgabe am Limit). Unten der "
                    "vermeidbare Netzbezug je Stunde. So sieht man, wann die Regelung nicht greift, etwa wenn ein "
                    "Zeitfenster in der App des Herstellers Vorrang hat.",),
    },
    "nulleinspeisung": {
        "regelbereit_stunden": ("Zeit, in der der Speicher mehr hätte abgeben können: Akku über der Untergrenze, Abgabe "
                                "unter dem Limit. Nur diese Zeit wird bewertet.",),
        "anteil_nahe_null": ("Anteil der regelbereiten Zeit, in der der Netzanschluss bei ±50 W lag. Je höher, desto "
                             "besser regelt der Speicher.", 0.8, 0.5, "≥ 80 %", "≤ 50 %"),
        "median_netz": ("Typische Netzleistung (Median) in der regelbereiten Zeit, + heißt Bezug. Nahe 0 W ist gut.",
                        50, 200, "≤ 50 W", "≥ 200 W"),
        "vermeidbarer_netzbezug": ("Netzbezug, den der Speicher im Rahmen seines Limits hätte decken können. Je kleiner, "
                                   "desto besser.", 1, 5, "≤ 1 kWh", "≥ 5 kWh"),
        "einspeisung": ("Strom, der ins Netz ging, und sein Wert, wäre er selbst verbraucht worden. Je kleiner, desto "
                        "besser.", 0.5, 3, "≤ 0,5 kWh", "≥ 3 kWh"),
        "lastspruenge": ("Wie oft die Netzleistung zwischen zwei Messungen um mehr als 300 W stieg, z. B. Wasserkocher "
                         "an. Grundlage für die Reaktionszeit.",),
        "reaktionszeit_median": ("Typische Zeit nach einem Lastsprung, bis der Netzanschluss wieder bei ±50 W liegt. Je "
                                 "kürzer, desto besser.", 15, 60, "≤ 15 s", "≥ 60 s"),
        "anteil_ueber_limit": ("Anteil der Zeit, in der die Abgabe ins Haus über dem eingestellten Limit lag. Sollte nahe "
                               "0 % sein.", 0.01, 0.05, "≤ 1 %", "≥ 5 %"),
    },
}


def guete(bereich, key, value):
    """Bewertung von 0 (schlecht) bis 1 (gut) laut KACHELN, None ohne Bewertung oder Wert."""
    entry = KACHELN[bereich][key]
    if len(entry) == 1 or not isinstance(value, (int, float)):
        return None
    _, good, bad, *_ = entry
    return min(max((value - bad) / (good - bad), 0.0), 1.0)


def parse_day(text, today):
    """Datum aus Text (JJJJ-MM-TT), bei leerer oder ungültiger Angabe today."""
    try:
        return date.fromisoformat(text) if text else today
    except ValueError:
        return today


def history(storage, view, datum, prices, now, forecast=None):
    """Balken einer Verlaufsansicht (tag, woche, monat, jahr) und Bilanz des Zeitraums; forecast: erwartete Erzeugung
    je Stunde (nur heute bekannt), für die Tagesansicht."""
    today = datetime.fromtimestamp(now, analytics.TZ).date()
    view = view if view in VIEWS else "tag"
    title, buckets, prev, nxt = analytics.buckets(view, parse_day(datum, today))
    rows = storage.hourly(int(now))
    return {"ansicht": view, "titel": title, "zurueck": prev, "weiter": nxt if nxt <= today else None,
            "balken": analytics.history(rows, buckets, prices, forecast if view == "tag" else None),
            "bilanz": analytics.balance([r for r in rows if r[1] < buckets[-1][2]], buckets[0][1], prices)}


def report(storage, monat, prices, now, commissioned=None):
    """Monatsbericht (monat=JJJJ-MM, sonst der laufende Monat) mit gespeicherter Regelgüte der Tage."""
    today = datetime.fromtimestamp(now, analytics.TZ).date()
    day = parse_day(monat + "-01" if monat else "", today)
    r = analytics.month_report(storage.hourly(int(now)), day, prices, commissioned)
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
