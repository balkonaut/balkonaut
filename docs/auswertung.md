# Auswertung

Balkonaut rechnet aus den Messwerten für **heute**, **diesen Monat**, **dieses Jahr** und **gesamt**
(Tagesgrenzen in deutscher Zeit). Die laufende Stunde zählt bis zum aktuellen Messwert mit.

## Übersicht

Solange Geräte, Standort und Flächen (im Add-on: Flächen oder eine Prognose-Entität) oder die Preise fehlen,
steht ganz oben die Kachel *Einrichtung* mit dem Stand der drei Schritte; sie verschwindet, sobald alle erledigt sind.
Die Startseite `http://<adresse>:8000/` zeigt oben die Ersparnis von heute, den Energiefluss, den Akku
und die Autarkie von heute. Darunter folgen die Bilanz für den gewählten Zeitraum, die Akku-Kennzahlen,
der heutige Hausverbrauch je Stunde (Anteil Balkonkraftwerk und Netz) und der Stand der Amortisation.
Die Werte aktualisieren sich alle 10 Sekunden, ohne dass die Seite neu lädt. Sind die letzten Messwerte älter als zwei Minuten, wird der Punkt
neben „Energiefluss jetzt“ orange und oben erscheint ein Hinweis: Dann sind meist die Geräte oder Home Assistant nicht erreichbar.

Jede Kachel mit einem Knopf **i** erklärt auf Druck kurz, was der Wert bedeutet. Werte mit klarer Güte tragen
zusätzlich eine Skala von Rot (links, schlecht) bis Grün (rechts, gut) mit Marke, die Grenzen darunter und ein Wort
(*gut*, *mittel*, *schwach*); siehe [Bewertung der Kennzahlen](#bewertung-der-kennzahlen).

Hell oder dunkel richtet sich zunächst nach der Einstellung des Geräts. Der Knopf rechts in der Kopfzeile wechselt
reihum zwischen *Automatisch*, *Hell* und *Dunkel*, die Wahl merkt sich der Browser. Unten auf jeder Seite stehen
die Version und ein Link zum Quellcode auf GitHub.

### Energiefluss

Das Bild zeigt, wohin die Leistung gerade fließt: von den **Modulen** in den Wechselrichter in der Mitte, von dort in
den **Akku** oder ins **Haus**, und zwischen **Netz** und Haus. Die Mitte trägt das Modell des Geräts (z. B. **EZHI**), in
der Integration aus dem Geräteregister von Home Assistant; ohne bekanntes Modell heißt sie **Wechselrichter**. Den Namen
des Akkus, z. B. den Hersteller, trägt man selbst ein (Docker-App: *Einstellungen → Preise und Anlage*, Integration:
*Konfigurieren*), weil die Geräte ihn nicht verlässlich melden; ohne Eintrag steht dort **Akku**. Ebenso für den
zweiten Wechselrichter: Ist er in Home Assistant ein eigenes Gerät, steht dort sein Modell, sonst die eingetragene
Bezeichnung (z. B. **EZ1-M**, wenn der Speicher ihn am Off-Grid-Port mitmisst) oder **Zusatz-WR**.
Je mehr Leistung, desto dicker die Leitung und desto schneller laufen die Pfeile. Ihre Spitze zeigt,
ob der Akku lädt oder entlädt und ob Strom aus dem Netz kommt oder eingespeist wird. Der Wert am Haus ist der
Hausverbrauch, also Abgabe des Balkonkraftwerks plus Netzbezug.

Ist ein zweiter Wechselrichter eingetragen (`pv_ac_power`, z. B. ein Mikrowechselrichter am Speicher), zeigt das
Bild oben zwei Modulfelder: links die Module am Speicher, rechts die Module am zweiten Wechselrichter, der als eigenes
Feld **Zusatz-WR** dazwischen steht. Die Module eines Wechselrichters teilen sich eine Anzeige, weil die Geräte keine
Werte je Modul liefern. Die Modulfelder tragen die Ausrichtung der Flächen (z. B. **Südost**, **West**): in der Docker-App aus den
Einstellungen, in der Integration aus den Forecast.Solar-Einträgen, die der Prognose des jeweiligen Wechselrichters
zugeordnet sind. Ohne Flächen heißen sie **Module**.

### Woher kommt dein Strom heute?

Das Diagramm zeigt je Stunde zwei Balken nebeneinander: **grün**, was das Balkonkraftwerk ins Haus abgegeben hat
(direkt von der Sonne oder aus dem Akku), **blau**, was aus dem Netz kam. Zusammen ergeben sie den Hausverbrauch.
Der **gelbe Strich** ist die Erzeugung aller Module in dieser Stunde, egal wohin sie ging; mit der Maus darüber steht
der Wert da.

| Gelber Strich liegt … | bedeutet |
|---|---|
| auf Höhe von Grün | die Erzeugung ging direkt ins Haus |
| deutlich über Grün | der Rest ging in den Akku oder ins Netz |
| unter Grün oder fehlt (nachts) | das Haus bekam Strom aus dem Akku |

Die **gestrichelte Linie** ist die erwartete Erzeugung je Stunde laut Forecast.Solar, alle Flächen zusammen. Sie
erscheint nur für heute und nur mit Tagesprognose: in der Docker-App und im Add-on aus den eingetragenen Flächen, in
der Integration aus der zugeordneten Forecast.Solar-Integration oder den Flächen unter *Konfigurieren*. Liegen die
gelben Striche deutlich unter der Linie, lohnt ein Blick auf den [Ertragswächter](#warnungen). Der Knopf **i** am
Diagramm erklärt das ebenfalls kurz. Dasselbe Diagramm zeigt die Seite *Verlauf* für Woche, Monat und Jahr, dort ohne
Prognose.

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

## Energiewege

Die Kachel unter der Bilanz zeigt für den gewählten Zeitraum, wohin die Energie geflossen ist (Docker-App, Add-on und
Panel der Integration):

| Wert | Bedeutung |
|---|---|
| Sonne erzeugt | Erzeugung aller Module, wie in der Bilanz |
| direkt ins Haus | Eigenverbrauch ohne den Anteil aus dem Akku |
| in den Akku geladen | Geladene Energie laut Zähler des Speichers (`battery_charge_energy`), sonst aus der Akkuleistung |
| eingespeist | Einspeisung ins Netz, wie in der Bilanz |
| Akku entladen | Entladene Energie laut Zähler des Speichers (`battery_discharge_energy`), sonst aus der Akkuleistung |
| davon im Haus angekommen | Je Stunde die Entladung, höchstens aber der Eigenverbrauch dieser Stunde |
| Verluste und Netz | Rest der Entladung: Wandlungsverluste und, was ins Netz ging |

Die Aufteilung rechnet mit Stundenwerten und braucht die Messgrößen `battery_power` und `output_power`, sonst steht
dort ein Strich. In Stunden, in denen Sonne und Akku gleichzeitig liefern, zählt der Akku zuerst. Weil die Werte aus
verschiedenen Zählern stammen, ergeben die drei Wege der Sonne zusammen nicht immer genau die Erzeugung.

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
Tageswerte als Diagramm und die Akku-Kennzahlen. Bei der Nulleinspeisung im Bericht sind nur die Anteile (nahe 0 W,
Abgabe über Limit) bewertet; die Grenzen der übrigen Werte gelten für 7 Tage, nicht für einen Monat.
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

### Regelbereit: welche Zeiten zählen

Balkonaut misst alle 10 Sekunden Netzleistung, Abgabe des Speichers und Ladestand und prüft für jeden Messpunkt,
ob der Speicher überhaupt mehr hätte abgeben können:

- Der Akku liegt über der Untergrenze plus 2 %. Ein leerer Akku kann nicht nachregeln.
- Die eigene Abgabe liegt unter etwa 95 % des Limits. Am Limit kann er nicht mehr geben.

Nur diese Zeiten fließen in *Nahe 0 W*, *Vermeidbarer Netzbezug* und die Lastsprünge ein. Netzbezug bei leerem Akku
oder am Limit ist kein Regelfehler, sondern eine Grenze der Anlage (siehe *Stunden mit leerem Akku* im Abschnitt Akku).

### Werte lesen

| Wert | Regelt gut | Regelt nicht |
|---|---|---|
| Nahe 0 W | hoch, z. B. über 80 % | deutlich niedriger |
| Vermeidbarer Netzbezug | klein | groß, der Speicher hätte mehr abgeben können |
| Reaktionszeit | wenige Sekunden | lang oder viele *nicht ausgeregelt* |
| Einspeisung | gering | hoch, z. B. weil die Abgabe zu spät zurückgeht |

### Beispiel: Zeitfenster in der Hersteller-App

Viele Speicher lassen sich in der Hersteller-App nach Uhrzeit einstellen, beim APsystems EZHI in AP EasyPower etwa
„Überschussladen“ und „Ladevorgang zuerst“ mit einer Ausgangsleistung je Zeitfenster. Ob die Regelung über den
Zähler (z. B. Shelly Pro 3EM) in einem Fenster „Ladevorgang zuerst“ Vorrang hat, beschreibt der Hersteller nicht
(**nicht geprüft**). Hat der Modus Vorrang, lädt der Akku morgens mit der Sonne, der Speicher gibt dem Haus wenig ab
und das Haus bezieht Netzstrom. Weil der Akku dabei über der Untergrenze und die Abgabe unter dem Limit liegt, zählt
diese Zeit als regelbereit: Der Netzbezug erscheint als *Vermeidbarer Netzbezug* und *Nahe 0 W* sinkt.

*Wann* nicht geregelt wurde, zeigt die Karte *Nach Uhrzeit* unter den Kacheln: oben je Stunde der Anteil nahe 0 W
als Farbfeld (grün ab 80 %, rot bis 50 %, blass ohne regelbereite Zeit), unten der vermeidbare Netzbezug je Stunde,
beides über die letzten 7 Tage. Liegt ein rotes Feld mit hoher Säule genau im Zeitfenster „Ladevorgang zuerst“, hat
der Modus dort vermutlich Vorrang. Zur Bestätigung an einem sonnigen Tag im [Verlauf](#verlauf) oder in Home
Assistant Netzleistung, Akkuleistung und Abgabe in diesem Fenster vergleichen: Bleibt die Netzleistung nahe 0 W,
während der Akku lädt, regelt der Zähler; lädt der Akku mit voller Sonnenleistung und das Haus bezieht Netzstrom, hat
der Modus Vorrang. Die Karte gibt es in der Docker-App, im Add-on und im Panel der Integration.

## Bewertung der Kennzahlen

Diese Kacheln haben eine Skala von Rot bis Grün, in der Docker-App, im Add-on und im Panel der Integration. Zwischen
den Grenzen läuft die Farbe stufenlos. Die Grenzen gelten für alle Anlagen gleich und sind ein Richtwert, keine Norm.

| Kachel | gut | schlecht |
|---|---|---|
| Eigenverbrauchsquote | ≥ 90 % | ≤ 60 % |
| Wirkungsgrad Akku | ≥ 90 % | ≤ 75 % |
| Verluste Speicher-Wechselrichter | ≤ 5 % | ≥ 15 % |
| Nulleinspeisung: Davon nahe 0 W | ≥ 80 % | ≤ 50 % |
| Nulleinspeisung: Typische Netzleistung (Betrag) | ≤ 50 W | ≥ 200 W |
| Nulleinspeisung: Vermeidbarer Netzbezug (7 Tage) | ≤ 1 kWh | ≥ 5 kWh |
| Nulleinspeisung: Einspeisung (7 Tage) | ≤ 0,5 kWh | ≥ 3 kWh |
| Nulleinspeisung: Reaktionszeit | ≤ 15 s | ≥ 60 s |
| Nulleinspeisung: Abgabe über Limit | ≤ 1 % | ≥ 5 % |

Der Autarkiegrad bleibt ohne Farbe: Ein Balkonkraftwerk deckt selten mehr als 30 bis 40 % des Hausverbrauchs, die
Kachel wäre also fast immer rot, obwohl alles in Ordnung ist.

## Amortisation

- **Bisher gespart**: Stand des Abgabezählers am Einspeisepunkt mal gemessener Eigenverbrauchsquote
  mal Arbeitspreis. Der Zähler läuft meist seit Inbetriebnahme, damit zählen auch die Monate,
  bevor Balkonaut lief. Ohne Abgabezähler zählt nur der Messzeitraum.
- **Ersparnis pro Jahr**: Mit eingetragenem Datum der Inbetriebnahme die bisherige Ersparnis seit diesem Datum,
  sonst die Ersparnis der Messtage, jeweils aufs Jahr hochgerechnet. In der Docker-App und im Add-on rechnet
  Balkonaut mit dem **Jahresverlauf**, sobald es die Flächen kennt (in den Einstellungen eingetragen oder aus der
  Forecast.Solar-Integration in Home Assistant): Aus Standort, Neigung, Ausrichtung und Leistung der Flächen holt es
  den erwarteten Ertrag je Monat bei PVGIS (EU) und gewichtet den Zeitraum danach. Zehn Oktobertage zählen so nicht
  wie zehn Junitage. Ohne Flächen, und bisher immer in der Integration für Home Assistant, wird gleichmäßig über das
  Jahr gerechnet.
- **Amortisiert**: Monat, in dem die Anschaffungskosten voraussichtlich erreicht sind, und die Jahre bis dahin.
- **Plausibilität**: Ist der Abgabezähler höher, als ein Wechselrichter mit 1200 W Dauerleistung seit dem eingetragenen
  Datum hätte liefern können, erscheint ein Hinweis. Dann stimmt meist das Datum nicht.
- **Vollzyklen pro Jahr** (Bereich Akku): Vollzyklen seit Inbetriebnahme geteilt durch die Jahre seitdem.

!!! note "Näherung"
    Der Jahresverlauf berücksichtigt die Sonne, aber nicht, dass im Sommer mehr Strom übrig bleibt, als der Haushalt
    braucht. Bei hohem Eigenverbrauch im Sommer fällt die Hochrechnung aus Wintertagen deshalb etwas zu hoch aus.
    Das Profil wird beim Start des Containers geladen; nach Änderungen an Forecast.Solar den Container neu starten.
