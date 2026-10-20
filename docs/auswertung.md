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

## Amortisation

- **Bisher gespart**: Stand des Abgabezählers am Einspeisepunkt mal gemessener Eigenverbrauchsquote
  mal Arbeitspreis. Der Zähler läuft meist seit Inbetriebnahme, damit zählen auch die Monate,
  bevor Balkonaut lief. Ohne Abgabezähler zählt nur der Messzeitraum.
- **Ersparnis pro Jahr**: Durchschnitt pro Messtag mal 365.
- **Jahre bis zur Amortisation**: Anschaffungskosten minus bisher gespart, geteilt durch die Ersparnis pro Jahr.

!!! warning "Näherung"
    Die Hochrechnung aufs Jahr kennt noch keinen Jahresverlauf. Mit Daten aus Herbst oder Winter
    fällt sie zu niedrig aus, mit Sommerdaten zu hoch. Aussagekräftig wird sie nach einem vollen Jahr.
