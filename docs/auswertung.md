# Auswertung

Balkonaut rechnet aus den Messwerten für **heute**, **diesen Monat**, **dieses Jahr** und **gesamt**
(Tagesgrenzen in deutscher Zeit). Grundlage sind abgeschlossene Stunden, die laufende Stunde
erscheint also erst nach ihrem Ende.

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

## Amortisation

- **Bisher gespart**: Stand des Abgabezählers am Einspeisepunkt mal gemessener Eigenverbrauchsquote
  mal Arbeitspreis. Der Zähler läuft meist seit Inbetriebnahme, damit zählen auch die Monate,
  bevor Balkonaut lief. Ohne Abgabezähler zählt nur der Messzeitraum.
- **Ersparnis pro Jahr**: Durchschnitt pro Messtag mal 365.
- **Jahre bis zur Amortisation**: Anschaffungskosten minus bisher gespart, geteilt durch die Ersparnis pro Jahr.

!!! warning "Näherung"
    Die Hochrechnung aufs Jahr kennt noch keinen Jahresverlauf. Mit Daten aus Herbst oder Winter
    fällt sie zu niedrig aus, mit Sommerdaten zu hoch. Aussagekräftig wird sie nach einem vollen Jahr.
