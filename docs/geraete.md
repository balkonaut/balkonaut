# Unterstützte Geräte

Bei der [geführten Einrichtung](installation.md#gefuhrte-einrichtung) wählt man Geräte, nicht Entitäten. Für die
Geräte auf dieser Seite kennt Balkonaut die Entitäten der jeweiligen Integration in Home Assistant und belegt die
Messgrößen vor, wo es feststeht auch mit dem richtigen Vorzeichen.

!!! warning "Die meisten Geräte sind nicht geprüft"
    Nur die als **bestätigt** markierten Geräte wurden an einer echten Anlage getestet. Alle anderen sind **nicht
    geprüft**: Ihre Zuordnung ist aus dem Quellcode und der Dokumentation der jeweiligen Integration abgeleitet,
    ohne Gerät. Sie kann unvollständig oder falsch sein. Die Vorschläge in der Einrichtung daher mit den aktuellen
    Werten vergleichen und bei Bedarf korrigieren. Wer ein solches Gerät hat, hilft sehr mit einer Rückmeldung über
    [Gerät melden](installation.md#gerat-melden), auch wenn alles passt.

Der **Stand** sagt, woher das Wissen kommt:

- **bestätigt**: an einem echten Gerät geprüft
- **nicht geprüft**: aus dem Code und der Dokumentation der Integration abgeleitet, noch an keinem echten Gerät
  getestet

Die Spalte **Direkt per Adresse** sagt, ob Balkonaut das Gerät auch ohne diese Integration selbst abfragen kann
(siehe [Geräte direkt im Heimnetz](#gerate-direkt-im-heimnetz)). Bei *nein* ist die Integration nötig, bei
*gleichwertig* bringt sie Balkonaut keine weiteren Werte.

Die Spalte **Vorzeichen** sagt, ob die Richtung (Akku lädt oder entlädt, Netz Bezug oder Einspeisung) belegt ist.
*Belegt* heißt, Balkonaut dreht das Vorzeichen bei Bedarf selbst. *Prüfen* heißt, die Integration dokumentiert es
nicht; dann in der Einrichtung auf die aktuellen Werte achten, siehe [Richtung prüfen](#richtung-prufen).
*—* heißt, die vorbelegten Messgrößen haben keine Richtung (nur Erzeugung oder Ladestand).

## Speicher und Wechselrichter

| Gerät | Integration in Home Assistant | Messgrößen | Vorzeichen | Direkt per Adresse | Stand |
|---|---|---|---|---|---|
| APsystems EZHI | APsystems EZHI Local API (HACS) | PV, Akku mit Zählern, Kapazität und Ladegrenzen, Abgabe ins Haus, Off-Grid-Port, Abgabelimit | belegt | ja, ohne Ladegrenzen, Entladeschutz und Abgabelimit | bestätigt |
| APsystems EZ1-M | APsystems | PV-Leistung, PV-Zähler, Abgabelimit | — | nein | bestätigt |
| Deye (Hybrid und Mikrowechselrichter) | Solarman (HACS), Varianten von davidrapan und StephanJoubert | PV, Akku mit Zählern, Netz, Abgabe | Akku belegt, Netz prüfen | nein | nicht geprüft |
| Huawei SUN2000 mit LUNA2000 | Huawei Solar (HACS) | PV-Leistung, Akku mit Zählern, Kapazität und Ladegrenzen, Netz über Power Meter, Abgabe | belegt | nein | nicht geprüft |
| Hoymiles HM, HMS | OpenDTU oder AhoyDTU (MQTT), Hoymiles WiFi (HACS) | PV-Leistung, PV-Zähler (nicht bei Hoymiles WiFi) | — | ja über OpenDTU (gleichwertig) und AhoyDTU (ohne Zähler), nicht über Hoymiles WiFi | nicht geprüft |
| Anker Solix Solarbank | Anker Solix (HACS) | PV-Leistung, Akku, Abgabe ins Haus, Netz | Akku belegt, Netz prüfen | nein | nicht geprüft |
| Zendure SolarFlow, Hyper, AIO | Zendure (HACS) | PV mit Zähler, Akku mit Zählern, Kapazität und Ladegrenzen, Abgabe mit Zähler, Abgabelimit | belegt | nein | nicht geprüft |
| EcoFlow PowerStream, STREAM | EcoFlow Cloud (HACS) | Akku mit Ladegrenzen, Abgabe ins Haus; STREAM auch PV, Akku-Zähler und Netz | prüfen | nein | nicht geprüft |
| Growatt MIN, MIC, MOD, SPH | Growatt Server | PV mit Zähler, Ladestand, Akku-Zähler, Abgabe | — | nein | nicht geprüft |
| Victron GX (MultiPlus, Quattro, MPPT) | Victron GX, Victron MQTT (HACS) oder Victron Modbus (HACS) | PV und Akku mit Zählern, Netz; über Modbus nur Akku | GX und MQTT belegt, Modbus prüfen | ja über MQTT oder Modbus TCP am GX (ohne Zähler) | nicht geprüft |
| Fox ESS H1, H3, KH, EVO | FoxESS Modbus oder FoxESS Cloud (HACS) | PV mit Zähler, Akku mit Zählern und Ladegrenzen, Netz, Abgabe; Cloud nur PV und Akku | Modbus belegt, Cloud prüfen | nein | nicht geprüft |
| Marstek Venus C, D, E | Marstek Local API oder Marstek Modbus (HACS) | PV, Akku; über Modbus auch Zähler, Ladegrenzen und Abgabe | Local API belegt, Modbus prüfen | nein | nicht geprüft |
| Sungrow SH*RT, SH*K | Modbus-Vorlage von mkaiser (YAML) | PV und Akku mit Zählern, Kapazität und Ladegrenzen, Netz, Abgabe | belegt | nein | nicht geprüft |
| SolaX X1, X3 | SolaX Modbus (HACS) | PV mit Zähler, Akku mit Zählern, Netz, Abgabe | belegt | nein | nicht geprüft |

## Netzmessung und Einspeisepunkt

| Gerät | Integration in Home Assistant | Messgrößen | Vorzeichen | Direkt per Adresse | Stand |
|---|---|---|---|---|---|
| Shelly Pro 3EM | Shelly | Netzleistung über alle Phasen saldiert | belegt | ja, gleichwertig | bestätigt |
| Shelly Plug (Gen2, Gen3) | Shelly | Abgabe ins Haus, Zähler am Einspeisepunkt | prüfen (je nach Anschluss) | ja, gleichwertig | bestätigt |
| Shelly Pro EM, EM Gen3 | Shelly | Netzleistung an Kanal 0 | prüfen | ja, gleichwertig | nicht geprüft |
| Tibber Pulse | Tibber | Netzbezug | — | nein | nicht geprüft |

## Prognose

| Dienst | Integration in Home Assistant | Messgrößen | Stand |
|---|---|---|---|
| Forecast.Solar | Forecast.Solar | Tagesprognose je Fläche, benannt nach der Ausrichtung (z. B. Südost 150°) | bestätigt |

## Geräte direkt im Heimnetz

Diese Geräte liest Balkonaut selbst über deren lokale Schnittstelle, ohne Integration des Herstellers: die Docker-App
(*Einstellungen → Geräte*) und die Integration für Home Assistant (*Geräte direkt abfragen* in Schritt 2 der
[geführten Einrichtung](installation.md#gefuhrte-einrichtung)). Es genügt die IP-Adresse; Balkonaut fragt die Adresse
an und erkennt an der Antwort, welches Gerät dort läuft. Unbekannte Geräte meldet die Einrichtung.

Direkt abgefragt liefert der EZHI weniger als über seine Integration: Ladegrenzen, Entladeschutz und Abgabelimit
(nur über die APsystems-Cloud) fehlen, damit auch die Marken am Akku-Ring. Wer die Integration „APsystems EZHI Local API“ hat, ordnet
besser deren Entitäten zu.

| Gerät | IP-Adresse von | Messgrößen | Stand |
|---|---|---|---|
| APsystems EZHI | EZHI (lokalen Modus in der APsystems-App aktivieren) | PV, Off-Grid-Port, Akku mit Zählern und Kapazität, Abgabe ins Haus | bestätigt |
| Shelly Pro 3EM und andere Shelly mit drei Phasen | Shelly | Netzleistung über alle Phasen | bestätigt (Pro 3EM) |
| Shelly Plug (Gen2, Gen3) | Shelly | Abgabe ins Haus mit Zähler | bestätigt |
| Shelly Pro EM, EM Gen3 (eine Phase je Kanal) | Shelly | Netzleistung am ersten Kanal | nicht geprüft |
| Hoymiles über OpenDTU | OpenDTU | Erzeugung und Abgabe aller Wechselrichter zusammen, mit Zähler | nicht geprüft |
| Hoymiles über AhoyDTU | AhoyDTU | Erzeugung und Abgabe aller Wechselrichter zusammen, ohne Zähler | nicht geprüft |
| Victron GX (Cerbo GX, Venus GX, Ekrano GX) | GX (am GX unter *Einstellungen → Dienste* MQTT oder Modbus TCP einschalten) | PV am Laderegler, AC-gekoppelte PV als zusätzlicher Wechselrichter, Akku mit Ladestand, Netz über alle Phasen, Abgabe ins Haus, ohne Zähler | nicht geprüft, nur gegen einen Nachbau |

### Victron GX

Balkonaut liest beim GX die Systemwerte (`com.victronenergy.system`), dieselben, die die Übersicht am GX zeigt.
Über **Modbus TCP** (Port 502, Unit-ID 100) antwortet der GX sofort, das erkennt Balkonaut zuerst. Über **MQTT**
(Port 1883) fragt Balkonaut jedes Mal mit einem Keepalive alle Werte ab; die VRM-Portal-ID findet es selbst. Ist
beides eingeschaltet, genügt eines. Akku positiv beim Laden, Netz positiv beim Bezug, wie bei Victron. Die Abgabe ins Haus (PV und Akku zusammen)
ist der Verbrauch, den der GX misst, minus dem Netzbezug; daraus ergibt sich der Hausverbrauch. Zähler liefert
der GX für das System nicht, Balkonaut summiert die Leistung dann selbst auf. Über MQTT liest Balkonaut zusätzlich jeden
Laderegler (MPPT) einzeln, der Energiefluss zeigt dann ein Feld je Solarfeld. Ein Shelly als Netzmessung geht dem
Netzwert des GX vor.

### Hoymiles: welche IP-Adresse?

Die klassischen Hoymiles-Mikrowechselrichter haben selbst kein WLAN, sie funken mit einer DTU. Einzutragen ist
deshalb die IP-Adresse der DTU, nicht die des Wechselrichters:

| Was angeschlossen ist | IP-Adresse von | Direkt abfragbar |
|---|---|---|
| Hoymiles HM/HMS mit **OpenDTU** (ESP32-Box zum Selbstbauen) | OpenDTU | ja |
| Hoymiles HM/HMS mit **AhoyDTU** (ebenfalls ESP32) | AhoyDTU | ja |
| Hoymiles **HMS-…W-…T** mit eingebautem WLAN | – | nein, eigenes Protokoll |
| Hoymiles **DTU-Lite, DTU-Pro** (Boxen des Herstellers) | – | nein, Cloud bzw. Modbus |

Hängen mehrere Wechselrichter an einer DTU, zählt Balkonaut ihre Leistung zusammen. Ohne Speicher ist das die
Erzeugung und zugleich die Abgabe ins Haus; ein Shelly Plug am Einspeisepunkt hat für die Abgabe Vorrang. Die
Lesezugriffe der DTU müssen ohne Passwort erlaubt sein (Standard bei OpenDTU und AhoyDTU, nicht geprüft). AhoyDTU
liefert keinen Zähler, Balkonaut summiert die Leistung dann selbst auf.

### Was nicht direkt geht

Geräte mit Modbus (z. B. Sungrow, Huawei, Fox ESS, Deye) oder nur mit Cloud-Zugang (z. B. Anker Solix,
EcoFlow, Zendure, Growatt, Tibber) liest Balkonaut nicht selbst. Dafür gibt es zwei Wege: die
[Integration für Home Assistant](installation.md) mit der Integration des Herstellers, deren Entitäten Balkonaut für
viele dieser Geräte kennt (Tabellen oben), oder die Docker-App
mit dem Abschnitt `home_assistant` in der `config.yaml`, dann kommen die Werte aus Home Assistant
(siehe [Einstellungen](einstellungen.md)). Weitere Geräte kommen dazu, wenn jemand sie über
[Gerät melden](installation.md#gerat-melden) beisteuert.

## Lücken und Auswege

- **Ohne Zähler** (Anker Solix, Hoymiles WiFi, Huawei-PV, EcoFlow PowerStream): Balkonaut summiert die Leistung selbst
  auf. Das ist etwas ungenauer als ein Zähler, siehe [Messquellen](messquellen.md).
- **Growatt**: Akkuleistung und Netz liefert die Integration nur getrennt je Richtung, Balkonaut belegt sie deshalb
  nicht vor. Der **NOAH 2000** wird von der Growatt-Integration in Home Assistant nicht unterstützt.
- **Tibber Pulse**: Tibber liefert Bezug und Einspeisung als getrennte Sensoren. Balkonaut nimmt den Bezug; die
  Einspeisung fehlt damit.
- **Shelly 3EM (Gen1)**: Home Assistant bildet keine Summe über die Phasen. Einen Helfer der Integration *Min/Max* mit
  Typ *Summe* über die drei Phasenleistungen anlegen und diesen als Netzmessung zuordnen.
- **Entitäten ohne Gerät**, etwa aus einer Modbus-Vorlage in YAML: Balkonaut schlägt sie nur vor, wenn ein Profil sie
  genau kennt (z. B. Sungrow).
- **Andere Geräte**: Balkonaut schlägt eine Entität vor, wenn sie nach Art und Einheit eindeutig passt, etwa der
  einzige Leistungssensor des Geräts in W. Sonst bleibt das Feld leer und man wählt selbst.

## Richtung prüfen

Im Schritt *Entitäten prüfen* stehen die aktuellen Werte mit Richtung, z. B. „Netzleistung: 312 W (Bezug)“ oder
„Akkuleistung: 80 W (lädt)“. Passt die Richtung nicht zur Lage, die Messgröße unter *Vorzeichen drehen* wählen:

- **Netz**: Läuft ein großer Verbraucher und scheint keine Sonne, muss *Bezug* stehen.
- **Akku**: Lädt der Akku laut Hersteller-App, muss *lädt* stehen.
- **Abgabe ins Haus**: Gibt der Speicher Strom ab, steht keine Klammer; *Bezug, Vorzeichen prüfen* heißt gedreht.
- **PV**: Muss bei Sonne positiv sein; *negativ, Vorzeichen prüfen* heißt gedreht.

Später lässt sich das jederzeit über *⋮ → Neu konfigurieren* ändern, ohne Messdaten zu verlieren.
