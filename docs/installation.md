# Installation

Balkonaut läuft als Add-on in Home Assistant oder als eigener Docker-Container, zum Beispiel auf einer NAS.

## Als Home-Assistant-Add-on

Das Add-on braucht Home Assistant OS oder Supervised (dort gibt es den Add-on-Store, in neueren Versionen „Apps“).
Einen eigenen Server braucht es nicht, die Weboberfläche erscheint in der Seitenleiste von Home Assistant.

1. *Einstellungen → Add-ons → Add-on-Store*, oben rechts die drei Punkte → *Repositories*, dort
   `https://github.com/balkonaut/balkonaut` eintragen und *Hinzufügen*.
2. Im Store *Balkonaut* öffnen und *Installieren*.
3. Im Reiter *Konfiguration* unter *Entitäten* eintragen, welche Entität welche Messgröße liefert (Bedeutung siehe
   [Einstellungen](einstellungen.md)). Liefert eine Entität das umgekehrte Vorzeichen, die Messgröße unter
   *Vorzeichen drehen* auswählen, beim EZHI zum Beispiel *output_power*. *Speichern*.
4. *Starten* und *In Seitenleiste anzeigen* einschalten. Preise und Anschaffungskosten unter *Einstellungen* in
   Balkonaut eintragen.

Das Add-on greift über Home Assistant auf die Entitäten zu, ein Token ist nicht nötig. Alle Daten liegen im
Add-on und sind in den Backups von Home Assistant enthalten. Änderungen an den Entitäten wirken nach einem
Neustart des Add-ons. Die Übernahme des Verlaufs (siehe unten) ist im Add-on noch nicht möglich.

Für die [Integration](#home-assistant-integration) als Adresse die eintragen, die Balkonaut im Add-on unter
*Einstellungen* anzeigt (Form `http://…-balkonaut:8000`).

## Als Docker-Container

1. Repository herunterladen und in das Verzeichnis wechseln.
2. Konfiguration anlegen: `config.example.yaml` nach `data/config.yaml` kopieren und anpassen
   (siehe [Einstellungen](einstellungen.md)).
3. Container bauen und starten:

    ```bash
    docker compose up -d --build
    ```

4. Prüfen, ob der Dienst läuft: `http://<adresse>:8000/api/health` muss `{"status": "ok"}` liefern.

Alle Daten liegen im Ordner `data/`: Konfiguration (`config.yaml`) und Messdaten (`balkonaut.db`).
Für ein Backup genügt es, diesen Ordner zu sichern.

## Image automatisch bauen (Gitea Actions)

Liegt das Repository in einer eigenen Gitea-Instanz, kann ein Gitea Runner auf der NAS bei jedem Push auf `main`
die Tests ausführen und das Image `balkonaut:latest` bauen (`.gitea/workflows/deploy.yml`):

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

3. Nach einem erfolgreichen Lauf den Container mit dem neuen Image neu erstellen, im Verzeichnis von Balkonaut:

    ```bash
    docker compose up -d
    ```

    oder in Dockhand den Stack neu starten. `git pull` und `--build` sind dafür nicht nötig.

Den Container selbst startet der Workflow bewusst nicht: Der Runner entfernt am Ende eines Jobs alle Container,
die der Job gestartet hat.

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

Die Integration holt die Werte der laufenden Balkonaut-App nach Home Assistant: 22 Sensoren (Bilanz für heute,
Monat und Jahr, Amortisation, Akku), einen Problem-Sensor und ein Ereignis für Warnungen. Die App muss dafür
laufen und von Home Assistant aus erreichbar sein.

### Installation über HACS

1. In Home Assistant *HACS* öffnen, oben rechts die drei Punkte → *Benutzerdefinierte Repositories*.
2. Als Repository `https://github.com/balkonaut/balkonaut` eintragen, Typ *Integration*, *Hinzufügen*.
3. In HACS nach *Balkonaut* suchen, *Herunterladen*, danach Home Assistant neu starten.
4. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Balkonaut*, Adresse der App eingeben
   (z. B. `http://192.168.1.10:8000`).

Neue Versionen bietet HACS danach als Update an.

### Manuelle Installation

Den Ordner `custom_components/balkonaut` aus dem Repository nach `config/custom_components/balkonaut` in Home
Assistant kopieren (z. B. mit dem Add-on *Samba share* oder *Studio Code Server*), Home Assistant neu starten und die
Integration wie oben hinzufügen. Updates müssen dann ebenfalls von Hand kopiert werden.

### Einstellungen, Diagnose, Störungen

- Das Abfrageintervall (Standard 5 Minuten) lässt sich unter *Konfigurieren* ändern.
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
