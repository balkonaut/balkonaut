# Home-Assistant-Integration

Die Integration bringt Balkonaut nach Home Assistant: 22 Sensoren (Bilanz für heute, Monat und Jahr,
Amortisation, Akku), einen Problem-Sensor und ein Ereignis für Warnungen, dazu eigene Ansichten in der Seitenleiste
und eine Karte für das Dashboard. Sie läuft auch unter Home Assistant OS, ohne eigenen Server.

Die Integration misst selbst. Balkonaut liest die Werte alle 10 Sekunden, aus Entitäten anderer Integrationen oder
direkt von den Geräten im Heimnetz, und speichert sie in `balkonaut/balkonaut.db` im Konfigurationsordner von Home
Assistant. Die [Docker-App](docker.md) braucht es dafür nicht. Beim ersten Start übernimmt Balkonaut einmalig den
Verlauf der zugeordneten Entitäten aus dem Recorder von Home Assistant (standardmäßig die letzten 10 Tage), die
Auswertung beginnt also nicht bei null. Die Einrichtung ist geführt, siehe [Geführte Einrichtung](#gefuhrte-einrichtung).
Arbeitspreis, Einspeisevergütung, Anschaffungskosten und Inbetriebnahme stehen danach unter *Konfigurieren*; ohne sie
sind die Euro-Beträge 0.

## Installation über HACS

1. In Home Assistant *HACS* öffnen, oben rechts die drei Punkte → *Benutzerdefinierte Repositories*.
2. Als Repository `https://github.com/balkonaut/balkonaut` eintragen, Typ *Integration*, *Hinzufügen*.
3. In HACS nach *Balkonaut* suchen, *Herunterladen*, danach Home Assistant neu starten.
4. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Balkonaut* und die
   [geführte Einrichtung](#gefuhrte-einrichtung) durchgehen.

Neue Versionen bietet HACS danach als Update an.

!!! note "HACS noch nicht installiert?"
    Unter Home Assistant OS: *Einstellungen → Apps* (in älteren Versionen *Add-ons*) → App-Store, oben rechts
    ⋮ → *Repositories*, `https://github.com/hacs/addons` hinzufügen. Danach ⋮ → *Nach Updates suchen*, die App
    **Get HACS** steht ganz unten im Abschnitt „HACS“. Installieren, starten und im *Protokoll* warten, bis sie fertig
    meldet. Home Assistant neu starten, die Seite neu laden, dann *Geräte & Dienste → Integration hinzufügen → HACS*
    und den angezeigten Code unter `https://github.com/login/device` bestätigen.

!!! note "Vorabversionen (Beta) testen"
    Beim *Herunterladen* in HACS lässt sich die Version wählen, z. B. eine `…-beta.N`. Damit HACS spätere Betas als
    Update anbietet: *Geräte & Dienste → HACS → Geräte → Balkonaut*, die Entität *Pre-release* aktivieren und
    einschalten. Betas am besten auf einer Testinstanz ausprobieren.

!!! warning "Nach einem Update die Seite neu laden"
    Nach einem Update von Balkonaut die Seite in Home Assistant einmal neu laden (Mac: Cmd+Shift+R, Windows: Strg+F5).
    Sonst zeigt der Browser noch das alte Panel, und die Seiten *Verlauf*, *Nulleinspeisung* oder *Bericht* lassen sich
    unter Umständen nicht öffnen.

## Geführte Einrichtung

Die Namen der Entitäten muss man nicht kennen. Die Einrichtung hat drei Schritte:

1. **Geräte wählen**: Netzmessung (z. B. Shelly Pro 3EM), Speicher oder Wechselrichter (z. B. APsystems EZHI),
   optional ein zusätzlicher Wechselrichter (z. B. ein EZ1-M am Off-Grid-Port) und eine Messung am Einspeisepunkt
   (z. B. ein Shelly Plug). Was man nicht hat, bleibt leer. Sind die Geräte nicht in Home Assistant eingebunden,
   bleibt alles leer und es geht mit *OK* weiter zu Schritt 2.
2. **Entitäten prüfen**: Ganz oben steht *Geräte direkt abfragen* (siehe unten). Balkonaut schlägt zu jeder Messgröße eine Entität vor, gruppiert nach Netz, Erzeugung, Akku,
   Abgabe ins Haus und Prognose. Jede Zuordnung lässt sich ändern oder ergänzen, Abschnitte ohne Vorschlag sind
   eingeklappt. Darüber stehen die aktuellen Werte mit Richtung, z. B. „Netzleistung: 312 W (Bezug)“ oder
   „Akkuleistung: 80 W (lädt)“. Passt die Richtung nicht, etwa „Abgabe ins Haus“ als Bezug während der Akku entlädt,
   die Messgröße unter *Vorzeichen drehen* wählen. Bei Prognosen von Forecast.Solar steht die
   Ausrichtung der Flächen dabei, z. B. „Prognose Wechselrichter 1 mit Speicher: 4,2 kWh (Südost 150°)“.
   Unter *Geräte direkt abfragen* lassen sich Adressen von Geräten eintragen, die Balkonaut selbst abfragt, ohne
   Integration des Herstellers in Home Assistant, durch Komma getrennt (z. B. `192.168.1.11, 192.168.1.20`). Den
   Gerätetyp erkennt Balkonaut selbst, wie in der Docker-App: APsystems EZHI (lokalen Modus in der App aktivieren),
   Shelly Pro 3EM, Shelly mit einer Phase, Shelly Plug, OpenDTU, AhoyDTU und Victron GX (MQTT oder Modbus TCP,
   nicht geprüft). Ihre Werte stehen mit „(Gerät)“ bei den
   aktuellen Werten. Ist für eine Messgröße zusätzlich eine Entität zugeordnet, geht die Entität vor.
3. **Zusammenfassung**: welche Funktionen mit der Zuordnung verfügbar sind und welche nicht, weil Messgrößen fehlen.
   *Speichern* schließt ab, *Zuordnung ändern* führt zurück zu Schritt 2.

Pflicht ist nur eine einzige Messgröße oder ein Gerät. Fehlt eine, entfällt nur die Funktion, die sie braucht.

!!! example "Beispiel: Geräte nicht in Home Assistant eingebunden"
    1. *Integration hinzufügen → Balkonaut → Eigenständig in Home Assistant*.
    2. *Geräte wählen*: alles leer lassen, *OK*.
    3. *Entitäten prüfen*: unter *Geräte direkt abfragen* die Adressen eintragen, z. B.
       `192.168.178.11, 192.168.178.168, 192.168.178.38` (Speicher, Netzmessung, Zwischenstecker). Die Abschnitte
       darunter bleiben leer, auch *Prognose*, wenn keine Forecast.Solar-Integration installiert ist. *OK*.
    4. *Zusammenfassung*: Sie zeigt, welche Funktionen verfügbar sind. Zum Prüfen der Richtungen *Zuordnung ändern*:
       Schritt 2 zeigt jetzt oben die aktuellen Werte der Geräte mit „(Gerät)“. Stimmt eine Richtung nicht, unter
       *Vorzeichen drehen* die Messgröße wählen, *OK*.
    5. In der Zusammenfassung *Speichern*.
    6. Danach unter *Konfigurieren* Arbeitspreis, Einspeisevergütung und Anschaffungskosten eintragen, optional das
       Datum der Inbetriebnahme und für die Tagesprognose die Flächen (siehe unten). Die Kachel *Einrichtung* im Panel
       zeigt, was noch fehlt.

!!! tip "Pro Gerät eine Quelle: Integration oder Adresse"
    Ein Gerät entweder über seine Integration in Home Assistant einbinden oder direkt über die Adresse, nicht beides.
    Sonst fragen zwei Stellen dasselbe Gerät ab, ohne dass es mehr Werte gibt. Beispiel APsystems EZHI:

    | Fall | Einrichtung | Ergebnis |
    |---|---|---|
    | Integration „APsystems EZHI Local API“ installiert | Schritt 1: EZHI als *Speicher oder Wechselrichter* wählen, keine Adresse eintragen | alle Messgrößen samt Akkukapazität, Ladegrenzen, Entladeschutz und Abgabelimit |
    | ohne diese Integration | Schritt 2: Adresse unter *Geräte direkt abfragen* | PV, Akku mit Zählern und Kapazität, Abgabe ins Haus, Off-Grid-Port; ohne Ladegrenzen, Entladeschutz und Abgabelimit, damit ohne Marken am Akku-Ring |

    Bei anderen Geräten steht in der Spalte *Direkt per Adresse* unter [Unterstützte Geräte](geraete.md), ob die
    Adresse reicht: bei Shelly und Hoymiles über OpenDTU gleichwertig, bei den meisten anderen Herstellern ist die
    Integration nötig.

    Die Integration lohnt sich auch, wenn man den EZHI aus Home Assistant steuern will (z. B. den Entladeschutz per
    Automation); Balkonaut liest nur.

### Tagesprognose: mit oder ohne Forecast.Solar-Integration

Die Tagesprognose ist optional. Sie braucht der [Ertragswächter](auswertung.md#warnungen), außerdem zeigt sie die
gestrichelte Linie im Diagramm und die Ausrichtung der Module im Energiefluss. Ohne Prognose fehlt nur das. Die
Werte kommen in beiden Fällen von Forecast.Solar, es gibt zwei Wege:

| | Forecast.Solar-Integration installiert | ohne diese Integration |
|---|---|---|
| Einrichtung | Schritt 2, Abschnitt *Prognose*: je Wechselrichter die Entität *Geschätzte Energieerzeugung – heute* des passenden Forecast.Solar-Eintrags zuordnen (nicht *Resttag heute*) | unter *Konfigurieren*: *Fläche Wechselrichter 1 mit Speicher* und gegebenenfalls *Fläche zusätzlicher Wechselrichter 2* mit Neigung, Ausrichtung und Leistung |
| Abruf bei Forecast.Solar | durch die Forecast.Solar-Integration, Balkonaut liest nur ihre Entität | durch Balkonaut selbst, zur vollen und halben Stunde, mit dem Standort aus Home Assistant |
| Flächen je Wechselrichter | mehrere, so viele wie im Forecast.Solar-Eintrag angelegt | eine |
| Linie im Diagramm, Ausrichtung im Energiefluss | aus den Flächen des Forecast.Solar-Eintrags | aus den eingetragenen Flächen |

Gibt es nur einen Forecast.Solar-Eintrag und keinen zweiten Wechselrichter, schlägt Balkonaut die Entität in Schritt 2
selbst vor. Bei den aktuellen Werten steht die Ausrichtung dabei, z. B. „Prognose Wechselrichter 1 mit Speicher: 4,2 kWh (Südost 150°)“;
so lässt sich prüfen, ob der richtige Eintrag dem richtigen Wechselrichter zugeordnet ist.

Beides gleichzeitig ist nicht nötig. Ist für einen Wechselrichter eine Prognose-Entität zugeordnet, gilt sie, und
Balkonaut ruft für diesen Wechselrichter nicht selbst ab, auch wenn dort eine Fläche eingetragen ist. Mischen geht:
etwa Forecast.Solar für den Speicher und eine eingetragene Fläche für den zweiten Wechselrichter.

!!! note "Abrufgrenze von Forecast.Solar"
    Ohne eigenen Schlüssel erlaubt Forecast.Solar 12 Abrufe je Stunde und öffentlicher IP-Adresse. Alle Geräte im
    Heimnetz teilen sich diese Grenze, also auch die Forecast.Solar-Integration und die Docker-App.
    Balkonaut braucht beim eigenen Abruf 2 Abrufe je Fläche und Stunde. Laufen Docker-App und Integration beide mit
    eingetragenen Flächen, zählt das doppelt; dann besser an einer Stelle die Forecast.Solar-Integration nutzen.

Danach zeigt das Balkonaut-Panel in der Seitenleiste oben die Kachel *Einrichtung*, solange etwas Wichtiges fehlt:
Messgrößen für Netz, Abgabe, Erzeugung und Ladestand (*⋮ → Neu konfigurieren*) sowie Arbeitspreis und Anlagekosten
(unter *Konfigurieren*). Prognose (Prognose-Entität oder Fläche) und Datum der Inbetriebnahme sind als Schritte
empfohlen, halten die Kachel aber nicht offen.

### Unterstützte Geräte

Welche Geräte Balkonaut kennt, welche davon geprüft sind und was bei den übrigen zu beachten ist, steht unter
[Unterstützte Geräte](geraete.md). Bei anderen Geräten schlägt Balkonaut eine Entität vor, wenn sie nach Art und
Einheit eindeutig passt, sonst wählt man selbst.

### Gerät melden

Damit ein weiteres Gerät dazukommt: Balkonaut einrichten, die Entitäten von Hand zuordnen, dann unter
*Einstellungen → Geräte & Dienste → Balkonaut → ⋮ → Diagnose herunterladen* und die Datei an ein
[Issue auf GitHub](https://github.com/balkonaut/balkonaut/issues) mit Hersteller, Modell und Integration hängen.

## Manuelle Installation

Unter *Releases* auf GitHub `balkonaut.zip` herunterladen, nach `config/custom_components/balkonaut` in Home
Assistant entpacken (z. B. mit dem Add-on *Samba share* oder *Studio Code Server*), Home Assistant neu starten und die
Integration wie oben hinzufügen. Updates müssen dann ebenfalls von Hand kopiert werden. Der Ordner im Repository
allein reicht nicht, weil er die Rechenlogik aus `core/` nur verlinkt; das Zip enthält sie.

## Umzug von der Docker-App

Wer bisher die Docker-App genutzt hat, kann deren Messdaten in die Integration übernehmen,
damit Monatsberichte, Jahr und Amortisation die ganze Historie kennen:

1. Die Integration wie oben einrichten.
2. Als Administrator *Entwicklerwerkzeuge → Aktionen*, die Aktion *Balkonaut: Historie aus Balkonaut-App übernehmen*
   wählen und die Adresse der laufenden App eintragen (z. B. `http://192.168.1.10:8000`), *Aktion ausführen*.

Stunden vor der ersten eigenen Messung der Integration werden durch die Werte der App ersetzt, die genauer
sind als der Verlauf aus dem Recorder. Was die Integration selbst gemessen hat, bleibt. Die Antwort nennt die
Zahl der übernommenen Stunden. Danach kann die App abgeschaltet werden. Die App muss mindestens die Version haben, die
`/api/v1/export` kennt (siehe [Schnittstelle](schnittstelle.md)).

## Balkonaut in der Seitenleiste

Sobald Balkonaut eingerichtet ist, erscheint *Balkonaut* in der Seitenleiste von Home Assistant. Dort gibt es dieselben Ansichten wie in der Docker-App: Übersicht mit Energiefluss, Bilanz, Akku,
heutigem Verlauf und Amortisation, außerdem *Verlauf*, *Nulleinspeisung* und den Monatsbericht zum Drucken.
*Einstellungen* führt zu den Optionen der Integration, *Handbuch* zu diesem Handbuch als Website
(https://balkonaut.github.io/balkonaut/).

## Karte für das Dashboard

Die Integration bringt eine Lovelace-Karte mit Energiefluss, Akku-Ring mit SoC-Grenzen und Restzeit sowie Ersparnis
und Autarkie von heute mit. Sie wird automatisch geladen, ein Eintrag unter *Ressourcen* ist nicht nötig. Im
Dashboard *Bearbeiten → Karte hinzufügen* und nach *Balkonaut* suchen, oder als YAML:

```yaml
type: custom:balkonaut-card
```

Die Karte holt ihre Werte alle 10 Sekunden selbst aus der letzten Messung. Optional: `title` für eine eigene
Überschrift.

## Einstellungen, Diagnose, Störungen

- Unter *Konfigurieren*: das Abfrageintervall (Standard 5 Minuten), die Bezeichnung des Akkus für den Energiefluss
  (optional, z. B. der Hersteller) und des zusätzlichen Wechselrichters (optional, z. B. EZ1-M), außerdem Preise,
  Anschaffungskosten und Inbetriebnahme.
- Ebenfalls unter *Konfigurieren*: je eine Fläche am Speicher und am zweiten Wechselrichter mit Neigung,
  Ausrichtung und Leistung, für die Tagesprognose ohne Forecast.Solar-Integration, siehe
  [Tagesprognose](#tagesprognose-mit-oder-ohne-forecastsolar-integration).
- Unter *⋮ → Neu konfigurieren*: die Zuordnung der Entitäten und die direkt abgefragten Geräte ändern (Schritte 2
  und 3 der [geführten Einrichtung](#gefuhrte-einrichtung)). Eintrag und Messdaten bleiben erhalten.
  Für neu zugeordnete Entitäten übernimmt Balkonaut keinen Verlauf aus dem Recorder, sie zählen ab der Änderung.
- Gibt es eine zugeordnete Entität nicht mehr oder ist sie deaktiviert, etwa weil die Integration des Geräts sie
  umbenannt hat, erscheint unter *Einstellungen → Reparaturen* ein Hinweis mit den betroffenen Entitäten und einem
  Link zu Balkonaut, dort über *Neu konfigurieren* neu zuordnen. Kurz nicht verfügbare Entitäten (Neustart, WLAN)
  lösen keinen Hinweis aus. Der Hinweis verschwindet, sobald alle Entitäten wieder da sind.
- Antwortet ein direkt abgefragtes Gerät dreimal hintereinander nicht, erscheint unter *Einstellungen → Reparaturen*
  ein Hinweis mit der Adresse. Er verschwindet, sobald das Gerät wieder antwortet. Die Adresse lässt sich über
  *Neu konfigurieren* ändern.
- Über *⋮ → Diagnose herunterladen* gibt es eine Datei mit Einstellungen und dem letzten Stand der Auswertung.
- Wer früher die Betriebsart *Mit einer Balkonaut-App* eingerichtet hatte, sieht unter *Einstellungen → Reparaturen*
  einen Hinweis: Diese Betriebsart gibt es nicht mehr. Den Eintrag löschen, Balkonaut neu hinzufügen und die
  Messdaten bei Bedarf wie unter [Umzug von der Docker-App](#umzug-von-der-docker-app) übernehmen.

## Benachrichtigung bei Warnungen

Der Problem-Sensor *Warnungen* ist an, solange eine Warnung besteht (Texte im Attribut `warnungen`). Das Ereignis
*Warnung* löst bei jeder neu auftretenden Warnung aus. Eine Benachrichtigung braucht damit kein Template
(`notify.mobile_app_…` an das eigene Gerät anpassen, Entitäts-ID ggf. anpassen, wenn das Gerät einem Bereich
zugeordnet ist):

```yaml
alias: Balkonaut Warnung
triggers:
  - trigger: state
    entity_id: event.balkonaut_warnung
    not_from: unavailable
    not_to:
      - unavailable
      - unknown
actions:
  - action: notify.mobile_app_mein_handy
    data:
      title: Balkonaut
      message: "{{ trigger.to_state.attributes.text }}"
mode: queued
```

## Umstieg von den REST-Sensoren

Wer vorher die REST-Sensoren aus [Schnittstelle](schnittstelle.md) genutzt hat: den `rest:`-Block aus der
`configuration.yaml` entfernen, Home Assistant neu starten und die verwaisten Einträge (Integration *RESTful*,
Status *nicht verfügbar*) unter *Einstellungen → Geräte & Dienste → Entitäten* löschen. Danach lassen sich die
Sensoren der Integration, die wegen belegter Namen auf `_2` enden, umbenennen.
