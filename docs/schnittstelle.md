# Schnittstelle (API)

Balkonaut stellt seine Werte als JSON bereit, z. B. für Home Assistant. Die Schnittstelle unter `/api/v1/`
bleibt stabil: Felder kommen höchstens hinzu, bestehende ändern sich erst mit `/api/v2/`.
Eine technische Übersicht aller Abfragen liefert `http://<adresse>:8000/docs`.

| Abfrage | Inhalt |
|---|---|
| `GET /api/v1/status` | Aktuelle Messwerte, Bilanz und Akku für heute, Monat, Jahr und gesamt, Amortisation |
| `GET /api/v1/verlauf?ansicht=tag\|woche\|monat\|jahr&datum=JJJJ-MM-TT` | Balken der Verlaufsansicht und Bilanz des Zeitraums |
| `GET /api/v1/nulleinspeisung` | Regelgüte der Nulleinspeisung der letzten 7 Tage |
| `GET /api/v1/bericht?monat=JJJJ-MM` | Monatsbericht: Bilanz, Vormonat, Vorjahresmonat, Akku, Erwartung, Tageswerte |
| `GET /api/v1/export` | Gesamte Historie (Stundenwerte, Tageswerte der Regelgüte) für den Umzug in die Integration |
| `GET /api/health` | `{"status": "ok"}`, wenn der Dienst läuft |

## Aufbau von `/api/v1/status`

- `warnungen`: Liste mit `code` (`keine_messwerte`, `ertrag_niedrig`, `ungleich`), `text` und ggf. `wechselrichter`
- `ertrag.speicher|ac`: `ertrag` und `prognose` (kWh) der letzten 7 vollen Tage, `quote` (Anteil), `tage`
- `stand`: Zeitpunkt des letzten Messwerts
- `live`: letzter Wert je Messgröße (Namen wie in den [Einstellungen](einstellungen.md), Leistung in W)
- `bilanz.tag|monat|jahr|gesamt`: `erzeugung`, `abgabe`, `netzbezug`, `einspeisung`, `eigenverbrauch`,
  `hausverbrauch` (kWh), `eigenverbrauchsquote`, `autarkiegrad` (Anteil 0 bis 1), `ersparnis` (€)
- `akku.tag|monat|jahr|gesamt`: `zyklen`, `zyklen_gesamt`, `zyklen_pro_jahr`, `gesundheit` (%), `kapazitaet` (kWh),
  `wirkungsgrad`, `verluste_wechselrichter` (Anteil 0 bis 1), `stunden_voll`, `einspeisung_bei_vollem_akku`,
  `stunden_leer`, `netzbezug_bei_leerem_akku` (kWh), `kosten_bei_leerem_akku` (€), `zusatz_kapazitaet`,
  `groesserer_akku` (kWh), `groesserer_akku_euro`, `groesserer_akku_jahr` (€, aufs Jahr hochgerechnet)
- `amortisation`: `kosten`, `bisher_gespart`, `ersparnis_pro_jahr`, `rest` (€), `basis` (`inbetriebnahme` oder
  `messtage`), `jahre_bis_amortisation`, `amortisiert_am` (Datum), `zaehler_plausibel`, `messtage`

Fehlt ein Wert (z. B. ohne Akku-Messgrößen), steht dort `null`.

## Werte als Sensoren in Home Assistant

Einfacher geht es mit der [Home-Assistant-Integration](installation.md#home-assistant-integration). Die REST-Sensoren
unten sind die Alternative ohne zusätzliche Dateien in Home Assistant.

Mit der REST-Integration von Home Assistant werden Werte zu Sensoren. Beispiel für die `configuration.yaml`:

```yaml
rest:
  - resource: http://<adresse>:8000/api/v1/status
    scan_interval: 300
    sensor:
      - name: Balkonaut Ersparnis heute
        unique_id: balkonaut_ersparnis_heute
        value_template: "{{ value_json.bilanz.tag.ersparnis | round(2) }}"
        unit_of_measurement: "€"
        device_class: monetary
      - name: Balkonaut Autarkie heute
        unique_id: balkonaut_autarkie_heute
        value_template: "{{ ((value_json.bilanz.tag.autarkiegrad or 0) * 100) | round(0) }}"
        unit_of_measurement: "%"
      - name: Balkonaut Ersparnis gesamt
        unique_id: balkonaut_ersparnis_gesamt
        value_template: "{{ value_json.amortisation.bisher_gespart | round(0) }}"
        unit_of_measurement: "€"
        device_class: monetary
      - name: Balkonaut amortisiert am
        unique_id: balkonaut_amortisiert_am
        value_template: "{{ value_json.amortisation.amortisiert_am }}"
        device_class: date
      - name: Balkonaut Warnungen
        unique_id: balkonaut_warnungen
        value_template: "{{ value_json.warnungen | count }}"
        json_attributes:
          - warnungen
      - name: Balkonaut Akku Vollzyklen
        unique_id: balkonaut_akku_vollzyklen
        value_template: "{{ value_json.akku.gesamt.zyklen_gesamt | round(0) }}"
```

Mit `unique_id` lassen sich die Sensoren in Home Assistant umbenennen und einem Bereich zuordnen. Sie stehen
nicht als eigenes Gerät unter *Geräte & Dienste*, sondern dort im Reiter *Entitäten* (Suche „balkonaut“).

## Benachrichtigung bei Warnungen

Der Sensor *Balkonaut Warnungen* zählt die Warnungen und trägt ihre Texte im Attribut `warnungen`. Eine
Automation, die sie aufs Handy schickt (`notify.mobile_app_…` an das eigene Gerät anpassen):

```yaml
alias: Balkonaut Warnung
triggers:
  - trigger: numeric_state
    entity_id: sensor.balkonaut_warnungen
    above: 0
actions:
  - action: notify.mobile_app_mein_handy
    data:
      title: Balkonaut
      message: >
        {{ state_attr('sensor.balkonaut_warnungen', 'warnungen') | map(attribute='text') | join('\n') }}
mode: single
```

Nach dem Ändern der `configuration.yaml` in Home Assistant *Entwicklerwerkzeuge → YAML → REST-Entitäten neu laden*
oder Home Assistant neu starten.
