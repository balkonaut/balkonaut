# Auswertung

Balkonaut rechnet aus den Messwerten für **heute**, **diesen Monat**, **dieses Jahr** und **gesamt**
(Tagesgrenzen in deutscher Zeit). Die laufende Stunde zählt bis zum aktuellen Messwert mit.

## Übersicht

Die Startseite `http://<adresse>:8000/` zeigt die aktuellen Leistungswerte, die Bilanz für den
gewählten Zeitraum, den heutigen Hausverbrauch je Stunde (Anteil Balkonkraftwerk und Netz) und den
Stand der Amortisation. Sie lädt sich jede Minute neu. Sind die letzten Messwerte älter als
zwei Minuten, erscheint ein Hinweis: Dann ist meist Home Assistant nicht erreichbar.

## Begriffe

| Wert | Bedeutung |
|---|---|
| Erzeugung | PV-Erzeugung aller Wechselrichter |
| Abgabe | Was das Balkonkraftwerk (inklusive Akku) ins Hausnetz abgibt |
| Netzbezug | Strom aus dem Netz |
| Einspeisung | Strom ins Netz |
| Eigenverbrauch | Abgabe minus Einspeisung: der Teil, den der Haushalt selbst verbraucht |
| Hausverbrauch | Netzbezug plus Eigenverbrauch |
| Eigenverbrauchsquote | Anteil der Abgabe, der im Haushalt bleibt |
| Autarkiegrad | Anteil des Hausverbrauchs, den das Balkonkraftwerk deckt |
| Ersparnis | Eigenverbrauch × Arbeitspreis + Einspeisung × Einspeisevergütung |

## Akku

| Wert | Bedeutung |
|---|---|
| Vollzyklen | Entladene Energie geteilt durch die nutzbare Kapazität. „Gesamt“ zählt seit Inbetriebnahme des Speichers |
| Gesundheit (SoH) | Vom Speicher gemeldeter Zustand in % der ursprünglichen Kapazität |
| Wirkungsgrad Akku | Entladene Energie plus Änderung des Ladestands, geteilt durch geladene Energie. Erst ab etwa 0,5 kWh Ladung im Zeitraum aussagekräftig |
| Verluste Speicher-Wechselrichter | Anteil der Energie, die im Speicher-Wechselrichter verloren geht: Eingänge (PV, weitere Wechselrichter, Netzladung, Entladen) gegen Ausgänge (Abgabe, Laden) |
| Stunden mit vollem Akku | Stunden mit Ladestand nahe der eingestellten Obergrenze. Bei Nulleinspeisung wird überschüssige PV-Leistung dann meist abgeregelt, ein größerer Akku könnte sie speichern |
| Stunden mit leerem Akku | Stunden mit Ladestand nahe der Untergrenze. Der Netzbezug in diesen Stunden ist die Obergrenze dessen, was ein größerer Akku hätte abdecken können, sofern genug Überschuss da gewesen wäre |

Für Kapazität, Gesundheit und Ladegrenzen braucht Balkonaut die optionalen Messgrößen
`battery_capacity`, `battery_soh`, `battery_soc_min` und `battery_soc_max` (siehe [Einstellungen](einstellungen.md)).

## Nulleinspeisung

Die Seite *Nulleinspeisung* zeigt für die letzten 7 Tage, wie gut der Speicher den Netzanschluss auf 0 W regelt.
Bewertet werden nur Zeiten, in denen er nachregeln konnte: Akku über der Untergrenze und eigene Abgabe
unter dem eingestellten Limit. Strom, den ein weiterer Wechselrichter am Speicher (z. B. ein EZ1-M) nur
durchreicht, zählt dabei nicht zur eigenen Abgabe.

| Wert | Bedeutung |
|---|---|
| Regelbereit | Stunden, in denen der Speicher hätte nachregeln können |
| Nahe 0 W | Anteil dieser Zeit mit Netzleistung zwischen −50 W und +50 W |
| Vermeidbarer Netzbezug | Netzbezug in dieser Zeit, den der Speicher im Rahmen seines Limits hätte decken können |
| Einspeisung | Strom, der ins Netz ging, und sein Wert, wäre er selbst verbraucht worden |
| Lastsprünge, Reaktionszeit | Anstiege der Netzleistung um mehr als 300 W und die Zeit, bis wieder ±50 W erreicht sind (Messraster 10 s) |
| Abgabe über Limit | Anteil der Zeit, in der die Abgabe ins Hausnetz über dem eingestellten Limit lag |

Das Limit liest Balkonaut aus der optionalen Messgröße `output_power_limit`, ohne Angabe gilt 800 W.
Alle Werte setzen eine korrekte Netzmessung voraus.

## Amortisation

- **Bisher gespart**: Stand des Abgabezählers am Einspeisepunkt mal gemessener Eigenverbrauchsquote
  mal Arbeitspreis. Der Zähler läuft meist seit Inbetriebnahme, damit zählen auch die Monate,
  bevor Balkonaut lief. Ohne Abgabezähler zählt nur der Messzeitraum.
- **Ersparnis pro Jahr**: Mit eingetragenem Datum der Inbetriebnahme die bisherige Ersparnis geteilt durch
  die Jahre seitdem. Ohne Datum der Durchschnitt pro Messtag mal 365.
- **Amortisiert**: Monat, in dem die Anschaffungskosten voraussichtlich erreicht sind, und die Jahre bis dahin.
- **Plausibilität**: Ist der Abgabezähler höher, als ein Wechselrichter mit 1200 W Dauerleistung seit dem eingetragenen
  Datum hätte liefern können, erscheint ein Hinweis. Dann stimmt meist das Datum nicht.
- **Vollzyklen pro Jahr** (Bereich Akku): Vollzyklen seit Inbetriebnahme geteilt durch die Jahre seitdem.

!!! warning "Näherung ohne Datum der Inbetriebnahme"
    Die Hochrechnung aus den Messtagen kennt keinen Jahresverlauf. Mit Daten aus Herbst oder Winter
    fällt sie zu niedrig aus, mit Sommerdaten zu hoch. Aussagekräftig wird sie nach einem vollen Jahr.
