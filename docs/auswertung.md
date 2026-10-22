# Auswertung

Balkonaut rechnet aus den Messwerten für **heute**, **diesen Monat**, **dieses Jahr** und **gesamt**
(Tagesgrenzen in deutscher Zeit). Die laufende Stunde zählt bis zum aktuellen Messwert mit.

## Übersicht

Die Startseite `http://<adresse>:8000/` zeigt oben die Ersparnis von heute, den Energiefluss, den Akku
und die Autarkie von heute. Darunter folgen die Bilanz für den gewählten Zeitraum, die Akku-Kennzahlen,
der heutige Hausverbrauch je Stunde (Anteil Balkonkraftwerk und Netz) und der Stand der Amortisation.
Die Seite lädt sich jede Minute neu. Sind die letzten Messwerte älter als zwei Minuten, wird der Punkt
neben „Energiefluss jetzt“ orange und oben erscheint ein Hinweis: Dann ist meist Home Assistant nicht erreichbar.

Hell oder dunkel richtet sich nach der Einstellung des Geräts.

### Energiefluss

Das Bild zeigt, wohin die Leistung gerade fließt: von der **Sonne** (beide Wechselrichter zusammen) in den
Speicher-Wechselrichter, von dort in den **Akku** oder ins **Haus**, und zwischen **Netz** und Haus.
Je mehr Leistung, desto dicker die Leitung und desto schneller laufen die Striche. Die Laufrichtung zeigt,
ob der Akku lädt oder entlädt und ob Strom aus dem Netz kommt oder eingespeist wird. Der Wert am Haus ist der
Hausverbrauch, also Abgabe des Balkonkraftwerks plus Netzbezug.

### Akku

Der Ring zeigt den Ladestand. Seine Farbe geht von Rot an der eingestellten Untergrenze bis Grün an der
Obergrenze. Die Grenzen erscheinen als farbige Striche im Ring und im Akku-Feld des Energieflusses, die
Bereiche außerhalb sind abgedunkelt:

| Strich | Bedeutung | Messgröße |
|---|---|---|
| rot | Minimum, darunter entlädt der Speicher nicht | `battery_soc_min` |
| orange | Entladeschutz | `battery_discharge_protection` |
| grün | Maximum, darüber lädt der Speicher nicht | `battery_soc_max` |

Alle drei sind optional (siehe [Einstellungen](einstellungen.md)). Fehlen die Grenzen, rechnet die Farbe mit 0 bis 100 %.

Lädt oder entlädt der Akku, steht unter dem Ladestand, wann er bei gleichbleibender Leistung die Obergrenze bzw. die
Untergrenze erreicht (beim Entladen der höhere Wert aus Minimum und Entladeschutz). Dafür braucht Balkonaut die
Akkukapazität (`battery_capacity`). Wandlungsverluste sind nicht eingerechnet, die Angabe ist deshalb etwas optimistisch.

## Verlauf

Die Seite *Verlauf* zeigt Tag (Stunden), Woche, Monat (je Tag) und Jahr (je Monat) als Balkendiagramm:
grün der Teil des Hausverbrauchs, den das Balkonkraftwerk gedeckt hat, blau der Netzbezug, der gelbe Strich
die Erzeugung. Mit *zurück* und *weiter* blätterst du durch die Zeiträume, darunter steht die Bilanz des
gewählten Zeitraums.

## Warnungen

Die Übersicht zeigt Warnungen oben an, die Schnittstelle liefert sie unter `warnungen`:

| Warnung | Wann |
|---|---|
| Keine Messwerte | Seit über 2 Minuten kam nichts von Home Assistant |
| Ertrag niedrig | Ein Wechselrichter lieferte in den letzten 7 Tagen weniger als 60 % der Prognose seiner Fläche |
| Ungleich | Ein Wechselrichter erreicht seine Prognose deutlich schlechter als der andere. Weil beide unter demselben Wetter arbeiten, deutet das auf Verschattung, Verschmutzung oder einen Defekt an einem Modulpaar |

Für die Ertragswarnungen braucht Balkonaut die Prognose je Fläche (`pv_forecast_today`, `pv_ac_forecast_today`,
siehe [Einstellungen](einstellungen.md)) und mindestens 3 Tage Daten. Ein voller Akku kann die Erzeugung am Speicher
abregeln und so eine Warnung „Ertrag niedrig“ auslösen, obwohl alles in Ordnung ist.

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

## Monatsbericht

Die Seite *Bericht* fasst einen Monat zusammen: Bilanz im Vergleich zu Vormonat und Vorjahresmonat,
erzeugte gegen laut PVGIS erwartete Energie, Tageswerte als Diagramm und die Akku-Kennzahlen.
Mit *Drucken / als PDF speichern* entsteht daraus eine druckfertige Seite oder PDF-Datei. Die Regelgüte der
Nulleinspeisung speichert Balkonaut einmal pro Tag für den Vortag, der Bericht fasst diese Tageswerte zusammen.
Sie beginnen mit dem Tag, an dem Balkonaut selbst zu messen begann; importierter Verlauf enthält keine 10-Sekunden-Werte.

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
- **Ersparnis pro Jahr**: Mit eingetragenem Datum der Inbetriebnahme die bisherige Ersparnis seit diesem Datum,
  sonst die Ersparnis der Messtage, jeweils aufs Jahr hochgerechnet. Ist die Forecast.Solar-Integration in Home
  Assistant eingerichtet, rechnet Balkonaut mit dem **Jahresverlauf**: Aus Standort, Neigung, Ausrichtung und
  Leistung der Flächen holt es den erwarteten Ertrag je Monat bei PVGIS (EU) und gewichtet den Zeitraum danach.
  Zehn Oktobertage zählen so nicht wie zehn Junitage. Ohne Forecast.Solar wird gleichmäßig über das Jahr gerechnet.
- **Amortisiert**: Monat, in dem die Anschaffungskosten voraussichtlich erreicht sind, und die Jahre bis dahin.
- **Plausibilität**: Ist der Abgabezähler höher, als ein Wechselrichter mit 1200 W Dauerleistung seit dem eingetragenen
  Datum hätte liefern können, erscheint ein Hinweis. Dann stimmt meist das Datum nicht.
- **Vollzyklen pro Jahr** (Bereich Akku): Vollzyklen seit Inbetriebnahme geteilt durch die Jahre seitdem.

!!! note "Näherung"
    Der Jahresverlauf berücksichtigt die Sonne, aber nicht, dass im Sommer mehr Strom übrig bleibt, als der Haushalt
    braucht. Bei hohem Eigenverbrauch im Sommer fällt die Hochrechnung aus Wintertagen deshalb etwas zu hoch aus.
    Das Profil wird beim Start des Containers geladen; nach Änderungen an Forecast.Solar den Container neu starten.
