# Installation

Balkonaut läuft als Add-on in Home Assistant oder als eigener Docker-Container, zum Beispiel auf einer NAS.

## Als Home-Assistant-Add-on

Das Add-on braucht Home Assistant OS oder Supervised (dort gibt es den Add-on-Store, in neueren Versionen „Apps“).
Einen eigenen Server braucht es nicht, die Weboberfläche erscheint in der Seitenleiste von Home Assistant.

1. *Einstellungen → Apps* (in älteren Versionen *Add-ons*) öffnen, dort den Store, oben rechts die drei Punkte →
   *Repositories*, `https://github.com/balkonaut/balkonaut` eintragen und *Hinzufügen*.
2. Im Store *Balkonaut* öffnen und *Installieren*.
3. Im Reiter *Konfiguration* unter *Entitäten* eintragen, welche Entität welche Messgröße liefert (Bedeutung siehe
   [Einstellungen](einstellungen.md)). Liefert eine Entität das umgekehrte Vorzeichen, die Messgröße unter
   *Vorzeichen drehen* auswählen, beim EZHI zum Beispiel *output_power*. *Speichern*.
4. *Starten* und *In Seitenleiste anzeigen* einschalten. Preise und Anschaffungskosten unter *Einstellungen* in
   Balkonaut eintragen. Die Kachel *Einrichtung* auf der Übersicht zeigt, was noch fehlt; Entitäten und die
   Entität der Tagesprognose kommen aus dem Reiter *Konfiguration* des Add-ons. Wer keine Forecast.Solar-Integration
   hat, trägt stattdessen unter *Einstellungen → Standort und Flächen* die Flächen ein; Balkonaut ruft die Prognose
   dann selbst ab, der Standort kommt aus Home Assistant.

Das Add-on greift über Home Assistant auf die Entitäten zu, ein Token ist nicht nötig. Alle Daten liegen im
Add-on und sind in den Backups von Home Assistant enthalten. Änderungen an den Entitäten wirken nach einem
Neustart des Add-ons. Die Übernahme des Verlaufs (siehe unten) ist im Add-on noch nicht möglich, wohl aber in der eigenständigen Integration.

Für die [Integration](#home-assistant-integration) als Adresse die eintragen, die Balkonaut im Add-on unter
*Einstellungen* anzeigt (Form `http://…-balkonaut:8000`).

Aus dem Handbuch geht es über *Zurück zu Balkonaut* im Menü oder über das Logo zurück zur Übersicht.

## Als Docker-Container

Balkonaut läuft auch ganz ohne Home Assistant, etwa auf einer NAS oder einem Raspberry Pi, und liest die Geräte
direkt im Heimnetz.

### Mit dem fertigen Image

1. Einen Ordner anlegen, darin eine Datei `docker-compose.yml`:

    ```yaml
    services:
      balkonaut:
        image: ghcr.io/balkonaut/balkonaut:latest
        ports:
          - "${BALKONAUT_PORT:-8000}:8000"
        volumes:
          - ./data:/data
        restart: unless-stopped
    ```

2. Starten: `docker compose up -d`
3. `http://<adresse>:8000/` öffnen und unter *Einstellungen* die Geräte per IP-Adresse hinzufügen, Standort und
   Flächen sowie Preise eintragen (siehe [Einstellungen](einstellungen.md)).
4. Neue Versionen holen: `docker compose pull && docker compose up -d`. Die Messdaten im Ordner `data/` bleiben.

In Dockhand geht das als neuer Stack mit diesem Inhalt oder als Git-Stack direkt aus dem Repository
`https://github.com/balkonaut/balkonaut`, dessen `docker-compose.yml` ebenfalls das fertige Image nutzt.
Aktualisiert wird dort über *Nach Updates suchen*.

Ist Port 8000 auf dem Rechner schon belegt, neben der `docker-compose.yml` eine Datei `.env` anlegen (Vorlage:
[`.env.example`](https://github.com/balkonaut/balkonaut/blob/main/.env.example)) mit zum Beispiel
`BALKONAUT_PORT=8080` (in Dockhand als Variable des Stacks). Balkonaut ist dann unter `http://<adresse>:8080/`
erreichbar.

Das Image gibt es für amd64 und arm64. Jede Version trägt zusätzlich einen Tag `sha-<commit>`, mit dem sich bei
Problemen eine ältere Version festhalten lässt.

### Selbst bauen

1. Repository herunterladen und in das Verzeichnis wechseln.
2. In `docker-compose.yml` die Zeile `# build: .` aktivieren (Raute entfernen), dann Container bauen und starten:

    ```bash
    docker compose up -d --build
    ```

3. `http://<adresse>:8000/` öffnen. Bis alles eingerichtet ist, zeigt die Übersicht oben die Kachel
   *Einrichtung* mit drei Schritten, jeweils mit Link zum passenden Abschnitt: unter *Einstellungen* die Geräte per IP-Adresse hinzufügen, Standort und Flächen eintragen, dann Preise und
   Kosten (siehe [Einstellungen](einstellungen.md)). Wer lieber eine Datei pflegt, kopiert `config.example.yaml`
   nach `data/config.yaml` und passt sie an.
4. Prüfen, ob der Dienst läuft: `http://<adresse>:8000/api/health` muss `{"status": "ok"}` liefern.

Alle Daten liegen im Ordner `data/`: Konfiguration (`config.yaml`) und Messdaten (`balkonaut.db`).
Für ein Backup genügt es, diesen Ordner zu sichern.

## Tests bei jedem Push (Gitea Actions)

Liegt das Repository in einer eigenen Gitea-Instanz, kann ein Gitea Runner auf der NAS bei jedem Push auf `main`
Tests, Integrationstests, hassfest und das Handbuch prüfen (`.gitea/workflows/deploy.yml`). Das Image selbst baut
GitHub als `ghcr.io/balkonaut/balkonaut:latest`, jede Release-Version zusätzlich mit eigenem Tag (z. B. `:1.0.0`); aktualisiert wird mit `docker compose pull && docker compose up -d`
oder in Dockhand über *Nach Updates suchen*.

1. In Gitea im Repository unter *Einstellungen → Actions → Runner* einen Runner anlegen und das Registrierungs-Token kopieren.
2. Den Runner auf der NAS starten:

    ```bash
    docker run -d --name gitea-runner --restart unless-stopped \
      -e GITEA_INSTANCE_URL=http://<gitea-adresse> \
      -e GITEA_RUNNER_REGISTRATION_TOKEN=<token> \
      -e GITEA_RUNNER_NAME=nas \
      -v <ordner>/gitea-runner:/data \
      -v /var/run/docker.sock:/var/run/docker.sock \
      docker.io/gitea/runner:3
    ```

!!! warning "Zugriff auf Docker"
    Der Runner hat über `/var/run/docker.sock` vollen Zugriff auf Docker und damit auf die NAS. Nur für eigene,
    private Repositories verwenden.

## Verlauf aus Home Assistant übernehmen

Home Assistant speichert standardmäßig die letzten zehn Tage. Diesen Verlauf kann Balkonaut einmalig
übernehmen, damit die Auswertung nicht bei null beginnt:

```bash
docker compose exec balkonaut python -m app.backfill 10
```

Die Zahl gibt an, wie viele Tage vor dem ersten eigenen Messwert übernommen werden.
Stunden, die Balkonaut schon selbst gemessen hat, bleiben unverändert. Der Befehl kann gefahrlos
mehrfach laufen.

## Home-Assistant-Integration

Die Integration bringt Balkonaut nach Home Assistant: 22 Sensoren (Bilanz für heute, Monat und Jahr,
Amortisation, Akku), einen Problem-Sensor und ein Ereignis für Warnungen. Beim Einrichten gibt es zwei Betriebsarten:

- **Eigenständig in Home Assistant**: Die Integration misst selbst. Balkonaut liest die Werte alle 10 Sekunden, aus
  Entitäten anderer Integrationen oder direkt von den Geräten im Heimnetz, und speichert sie in `balkonaut/balkonaut.db` im Konfigurationsordner von Home Assistant. Eine App, ein Container oder
  ein Add-on ist nicht nötig. Beim ersten Start übernimmt Balkonaut einmalig den Verlauf der zugeordneten Entitäten
  aus dem Recorder von Home Assistant (standardmäßig die letzten 10 Tage), die Auswertung beginnt also nicht bei null.
  Die Einrichtung ist geführt, siehe [Geführte Einrichtung](#gefuhrte-einrichtung). Arbeitspreis,
  Einspeisevergütung, Anschaffungskosten und Inbetriebnahme stehen danach unter *Konfigurieren*; ohne sie sind die
  Euro-Beträge 0.
- **Mit einer Balkonaut-App**: Die Integration holt die Werte von einer laufenden Docker-App oder dem Add-on ab. Die
  App muss laufen und von Home Assistant aus erreichbar sein.

### Installation über HACS

1. In Home Assistant *HACS* öffnen, oben rechts die drei Punkte → *Benutzerdefinierte Repositories*.
2. Als Repository `https://github.com/balkonaut/balkonaut` eintragen, Typ *Integration*, *Hinzufügen*.
3. In HACS nach *Balkonaut* suchen, *Herunterladen*, danach Home Assistant neu starten.
4. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Balkonaut*, Betriebsart wählen und entweder die
   [geführte Einrichtung](#gefuhrte-einrichtung) durchgehen oder die Adresse der App eingeben (z. B. `http://192.168.1.10:8000`).

Neue Versionen bietet HACS danach als Update an.

### Geführte Einrichtung

Im eigenständigen Betrieb muss man die Namen der Entitäten nicht kennen. Die Einrichtung hat drei Schritte:

1. **Geräte wählen**: Netzmessung (z. B. Shelly Pro 3EM), Speicher oder Wechselrichter (z. B. APsystems EZHI),
   optional ein zusätzlicher Wechselrichter (z. B. ein EZ1-M am Off-Grid-Port) und eine Messung am Einspeisepunkt
   (z. B. ein Shelly Plug). Was man nicht hat, bleibt leer.
2. **Entitäten prüfen**: Balkonaut schlägt zu jeder Messgröße eine Entität vor, gruppiert nach Netz, Erzeugung, Akku,
   Abgabe ins Haus und Prognose. Jede Zuordnung lässt sich ändern oder ergänzen, Abschnitte ohne Vorschlag sind
   eingeklappt. Darüber stehen die aktuellen Werte mit Richtung, z. B. „Netzleistung: 312 W (Bezug)“ oder
   „Akkuleistung: 80 W (lädt)“. Passt die Richtung nicht, etwa „Abgabe ins Haus“ als Bezug während der Akku entlädt,
   die Messgröße unter *Vorzeichen drehen* wählen. Bei Prognosen von Forecast.Solar steht die
   Ausrichtung der Flächen dabei, z. B. „Prognose Speicher: 4,2 kWh (Südost 150°)“.
   Unter *Geräte direkt abfragen* lassen sich Adressen von Geräten eintragen, die Balkonaut selbst abfragt, ohne
   Integration des Herstellers in Home Assistant, durch Komma getrennt (z. B. `192.168.1.11, 192.168.1.20`). Den
   Gerätetyp erkennt Balkonaut selbst, wie in der Docker-App: APsystems EZHI (lokalen Modus in der App aktivieren),
   Shelly Pro 3EM, Shelly mit einer Phase, Shelly Plug, OpenDTU und AhoyDTU. Ihre Werte stehen mit „(Gerät)“ bei den
   aktuellen Werten. Ist für eine Messgröße zusätzlich eine Entität zugeordnet, geht die Entität vor.
3. **Zusammenfassung**: welche Funktionen mit der Zuordnung verfügbar sind und welche nicht, weil Messgrößen fehlen.
   *Speichern* schließt ab, *Zuordnung ändern* führt zurück zu Schritt 2.

Pflicht ist nur eine einzige Messgröße oder ein Gerät.

!!! tip "Pro Gerät eine Quelle: Integration oder Adresse"
    Ein Gerät entweder über seine Integration in Home Assistant einbinden oder direkt über die Adresse, nicht beides.
    Sonst fragen zwei Stellen dasselbe Gerät ab, ohne dass es mehr Werte gibt. Beispiel APsystems EZHI:

    | Fall | Einrichtung | Ergebnis |
    |---|---|---|
    | Integration „APsystems EZHI Local API“ installiert | Schritt 1: EZHI als *Speicher oder Wechselrichter* wählen, keine Adresse eintragen | alle Messgrößen samt Akkukapazität, Ladegrenzen, Entladeschutz und Abgabelimit |
    | ohne diese Integration | Schritt 2: Adresse unter *Geräte direkt abfragen* | PV, Akku mit Zählern, Abgabe ins Haus, Off-Grid-Port; ohne Akkukapazität, Ladegrenzen, Entladeschutz und Abgabelimit, damit ohne Marken am Akku-Ring |

    Bei anderen Geräten steht in der Spalte *Direkt per Adresse* unter [Unterstützte Geräte](geraete.md), ob die
    Adresse reicht: bei Shelly und Hoymiles über OpenDTU gleichwertig, bei den meisten anderen Herstellern ist die
    Integration nötig.

    Die Integration lohnt sich auch, wenn man den EZHI aus Home Assistant steuern will (z. B. den Entladeschutz per
    Automation); Balkonaut liest nur. Fehlt eine, entfällt nur die Funktion, die sie braucht.

!!! note "Tagesprognose ist optional"
    Für die Tagesprognose des Ertragswächters entweder die Forecast.Solar-Integration einrichten und in Schritt 2
    unter *Prognose* zuordnen, oder später unter *Konfigurieren* eine Fläche je Wechselrichter eintragen; dann ruft
    Balkonaut die Prognose selbst bei Forecast.Solar ab. Ohne beides fehlt nur der Ertragswächter.

Danach zeigt das Balkonaut-Panel in der Seitenleiste oben die Kachel *Einrichtung*, solange etwas Wichtiges fehlt:
Messgrößen für Netz, Abgabe, Erzeugung und Ladestand (*⋮ → Neu konfigurieren*), eine Prognose-Entität oder eine
Fläche sowie Arbeitspreis und Anlagekosten (beides unter *Konfigurieren*). Das Datum der Inbetriebnahme ist als
vierter Schritt empfohlen, hält die Kachel aber nicht offen. Mit einer Balkonaut-App erscheint die Kachel nicht,
die App hat ihre eigene.

#### Unterstützte Geräte

Welche Geräte Balkonaut kennt, welche davon geprüft sind und was bei den übrigen zu beachten ist, steht unter
[Unterstützte Geräte](geraete.md). Bei anderen Geräten schlägt Balkonaut eine Entität vor, wenn sie nach Art und
Einheit eindeutig passt, sonst wählt man selbst.

#### Gerät melden

Damit ein weiteres Gerät dazukommt: Balkonaut einrichten, die Entitäten von Hand zuordnen, dann unter
*Einstellungen → Geräte & Dienste → Balkonaut → ⋮ → Diagnose herunterladen* und die Datei an ein
[Issue auf GitHub](https://github.com/balkonaut/balkonaut/issues) mit Hersteller, Modell und Integration hängen.

### Manuelle Installation

Unter *Releases* auf GitHub `balkonaut.zip` herunterladen, nach `config/custom_components/balkonaut` in Home
Assistant entpacken (z. B. mit dem Add-on *Samba share* oder *Studio Code Server*), Home Assistant neu starten und die
Integration wie oben hinzufügen. Updates müssen dann ebenfalls von Hand kopiert werden. Der Ordner im Repository
allein reicht nicht, weil er die Rechenlogik aus `core/` nur verlinkt; das Zip enthält sie.

### Umzug von Docker-App oder Add-on

Wer bisher die Docker-App oder das Add-on genutzt hat, kann deren Messdaten in den eigenständigen Eintrag übernehmen,
damit Monatsberichte, Jahr und Amortisation die ganze Historie kennen:

1. Den eigenständigen Eintrag wie oben einrichten.
2. Als Administrator *Entwicklerwerkzeuge → Aktionen*, die Aktion *Balkonaut: Historie aus Balkonaut-App übernehmen*
   wählen und die Adresse der laufenden App eintragen (z. B. `http://192.168.1.10:8000`), *Aktion ausführen*.

Stunden vor der ersten eigenen Messung des eigenständigen Eintrags werden durch die Werte der App ersetzt, die genauer
sind als der Verlauf aus dem Recorder. Was der eigenständige Eintrag selbst gemessen hat, bleibt. Die Antwort nennt die
Zahl der übernommenen Stunden. Danach kann die App abgeschaltet werden. Die App muss mindestens die Version haben, die
`/api/v1/export` kennt (siehe [Schnittstelle](schnittstelle.md)).

### Balkonaut in der Seitenleiste

Sobald ein Balkonaut-Eintrag eingerichtet ist, erscheint *Balkonaut* in der Seitenleiste von Home Assistant, in beiden
Betriebsarten. Dort gibt es dieselben Ansichten wie in der Docker-App: Übersicht mit Energiefluss, Bilanz, Akku,
heutigem Verlauf und Amortisation, außerdem *Verlauf*, *Nulleinspeisung* und den Monatsbericht zum Drucken.
*Einstellungen* führt zu den Optionen der Integration, *Handbuch* zu diesem Handbuch als Website
(https://balkonaut.github.io/balkonaut/).

### Karte für das Dashboard

Die Integration bringt eine Lovelace-Karte mit Energiefluss, Akku-Ring mit SoC-Grenzen und Restzeit sowie Ersparnis
und Autarkie von heute mit. Sie wird automatisch geladen, ein Eintrag unter *Ressourcen* ist nicht nötig. Im
Dashboard *Bearbeiten → Karte hinzufügen* und nach *Balkonaut* suchen, oder als YAML:

```yaml
type: custom:balkonaut-card
```

Die Karte holt ihre Werte alle 10 Sekunden selbst, im eigenständigen Betrieb aus der letzten Messung, mit einer
Balkonaut-App aus deren letztem Stand. Optional: `title` für eine eigene Überschrift, `entry_id`, wenn
mehrere Balkonaut-Einträge eingerichtet sind (ohne Angabe nimmt die Karte den eigenständigen).

### Einstellungen, Diagnose, Störungen

- Unter *Konfigurieren*: das Abfrageintervall (Standard 5 Minuten), die Bezeichnung des Akkus für den Energiefluss
  (optional, z. B. der Hersteller) und des zusätzlichen Wechselrichters (optional, z. B. EZ1-M), im eigenständigen Betrieb außerdem Preise, Anschaffungskosten und Inbetriebnahme.
- Ebenfalls unter *Konfigurieren* (eigenständig): je eine Fläche am Speicher und am zweiten Wechselrichter mit Neigung,
  Ausrichtung und Leistung. Wer keine Forecast.Solar-Integration hat, bekommt so trotzdem die Tagesprognose für den
  Ertragswächter: Balkonaut ruft sie zur vollen und halben Stunde selbst bei Forecast.Solar ab, mit dem Standort aus
  Home Assistant. Ist eine Prognose-Entität zugeordnet, geht sie vor. Bisher eine Fläche je Wechselrichter.
- Unter *⋮ → Neu konfigurieren*: im eigenständigen Betrieb die Zuordnung der Entitäten und die direkt abgefragten Geräte ändern (Schritte 2 und 3 der
  [geführten Einrichtung](#gefuhrte-einrichtung)), mit einer App deren Adresse. Eintrag und Messdaten bleiben erhalten.
  Für neu zugeordnete Entitäten übernimmt Balkonaut keinen Verlauf aus dem Recorder, sie zählen ab der Änderung.
- Gibt es eine zugeordnete Entität nicht mehr oder ist sie deaktiviert, etwa weil die Integration des Geräts sie
  umbenannt hat, erscheint unter *Einstellungen → Reparaturen* ein Hinweis mit den betroffenen Entitäten und einem
  Link zu Balkonaut, dort über *Neu konfigurieren* neu zuordnen. Kurz nicht verfügbare Entitäten (Neustart, WLAN)
  lösen keinen Hinweis aus. Der Hinweis verschwindet, sobald alle Entitäten wieder da sind.
- Antwortet ein direkt abgefragtes Gerät dreimal hintereinander nicht, erscheint unter *Einstellungen → Reparaturen*
  ein Hinweis mit der Adresse. Er verschwindet, sobald das Gerät wieder antwortet. Die Adresse lässt sich über
  *Neu konfigurieren* ändern.
- Antwortet die App dreimal hintereinander nicht, erscheint unter *Einstellungen → Reparaturen* ein Hinweis. Er
  verschwindet, sobald die App wieder antwortet.
- Über *⋮ → Diagnose herunterladen* gibt es eine Datei mit Einstellungen und letzter Antwort der App, die Adresse
  ist darin geschwärzt.

### Benachrichtigung bei Warnungen

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

### Umstieg von den REST-Sensoren

Wer vorher die REST-Sensoren aus [Schnittstelle](schnittstelle.md) genutzt hat: den `rest:`-Block aus der
`configuration.yaml` entfernen, Home Assistant neu starten und die verwaisten Einträge (Integration *RESTful*,
Status *nicht verfügbar*) unter *Einstellungen → Geräte & Dienste → Entitäten* löschen. Danach lassen sich die
Sensoren der Integration, die wegen belegter Namen auf `_2` enden, umbenennen.

## In Home Assistant einbinden

Übersicht und Handbuch lassen sich als eigene Dashboards in die Seitenleiste von Home Assistant holen:
*Einstellungen → Dashboards → Dashboard hinzufügen → Webseite*, als URL
`http://<adresse>:8000/` für die Übersicht oder `http://<adresse>:8000/handbuch/` für dieses Handbuch.

Wird Home Assistant über HTTPS aufgerufen, blockiert der Browser eine Seite mit `http://`.
Dann muss Balkonaut ebenfalls über HTTPS erreichbar sein, zum Beispiel über einen Reverse Proxy.
