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

Die Spalte **Vorzeichen** sagt, ob die Richtung (Akku lädt oder entlädt, Netz Bezug oder Einspeisung) belegt ist.
*Belegt* heißt, Balkonaut dreht das Vorzeichen bei Bedarf selbst. *Prüfen* heißt, die Integration dokumentiert es
nicht; dann in der Einrichtung auf die aktuellen Werte achten, siehe [Richtung prüfen](#richtung-prufen).
*—* heißt, die vorbelegten Messgrößen haben keine Richtung (nur Erzeugung oder Ladestand).

## Speicher und Wechselrichter

| Gerät | Integration in Home Assistant | Messgrößen | Vorzeichen | Stand |
|---|---|---|---|---|
| APsystems EZHI | APsystems EZHI Local API (HACS) | PV, Akku mit Zählern, Kapazität und Ladegrenzen, Abgabe ins Haus, Off-Grid-Port, Abgabelimit | belegt | bestätigt |
| APsystems EZ1-M | APsystems | PV-Leistung, PV-Zähler, Abgabelimit | — | bestätigt |
| Deye (Hybrid und Mikrowechselrichter) | Solarman (HACS), Varianten von davidrapan und StephanJoubert | PV, Akku mit Zählern, Netz, Abgabe | Akku belegt, Netz prüfen | nicht geprüft |
| Huawei SUN2000 mit LUNA2000 | Huawei Solar (HACS) | PV-Leistung, Akku mit Zählern, Kapazität und Ladegrenzen, Netz über Power Meter, Abgabe | belegt | nicht geprüft |
| Hoymiles HM, HMS | OpenDTU oder AhoyDTU (MQTT), Hoymiles WiFi (HACS) | PV-Leistung, PV-Zähler (nicht bei Hoymiles WiFi) | — | nicht geprüft |
| Anker Solix Solarbank | Anker Solix (HACS) | PV-Leistung, Akku, Abgabe ins Haus, Netz | Akku belegt, Netz prüfen | nicht geprüft |
| Zendure SolarFlow, Hyper, AIO | Zendure (HACS) | PV mit Zähler, Akku mit Zählern, Kapazität und Ladegrenzen, Abgabe mit Zähler, Abgabelimit | belegt | nicht geprüft |
| EcoFlow PowerStream, STREAM | EcoFlow Cloud (HACS) | Akku mit Ladegrenzen, Abgabe ins Haus; STREAM auch PV, Akku-Zähler und Netz | prüfen | nicht geprüft |
| Growatt MIN, MIC, MOD, SPH | Growatt Server | PV mit Zähler, Ladestand, Akku-Zähler, Abgabe | — | nicht geprüft |
| Victron GX (MultiPlus, Quattro, MPPT) | Victron GX, Victron MQTT (HACS) oder Victron Modbus (HACS) | PV und Akku mit Zählern, Netz; über Modbus nur Akku | GX und MQTT belegt, Modbus prüfen | nicht geprüft |
| Fox ESS H1, H3, KH, EVO | FoxESS Modbus oder FoxESS Cloud (HACS) | PV mit Zähler, Akku mit Zählern und Ladegrenzen, Netz, Abgabe; Cloud nur PV und Akku | Modbus belegt, Cloud prüfen | nicht geprüft |
| Marstek Venus C, D, E | Marstek Local API oder Marstek Modbus (HACS) | PV, Akku; über Modbus auch Zähler, Ladegrenzen und Abgabe | Local API belegt, Modbus prüfen | nicht geprüft |
| Sungrow SH*RT, SH*K | Modbus-Vorlage von mkaiser (YAML) | PV und Akku mit Zählern, Kapazität und Ladegrenzen, Netz, Abgabe | belegt | nicht geprüft |
| SolaX X1, X3 | SolaX Modbus (HACS) | PV mit Zähler, Akku mit Zählern, Netz, Abgabe | belegt | nicht geprüft |

## Netzmessung und Einspeisepunkt

| Gerät | Integration in Home Assistant | Messgrößen | Vorzeichen | Stand |
|---|---|---|---|---|
| Shelly Pro 3EM | Shelly | Netzleistung über alle Phasen saldiert | belegt | bestätigt |
| Shelly Plug (Gen2, Gen3) | Shelly | Abgabe ins Haus, Zähler am Einspeisepunkt | prüfen (je nach Anschluss) | bestätigt |
| Shelly Pro EM, EM Gen3 | Shelly | Netzleistung an Kanal 0 | prüfen | nicht geprüft |
| Tibber Pulse | Tibber | Netzbezug | — | nicht geprüft |

## Prognose

| Dienst | Integration in Home Assistant | Messgrößen | Stand |
|---|---|---|---|
| Forecast.Solar | Forecast.Solar | Tagesprognose je Fläche, benannt nach der Ausrichtung (z. B. Südost 150°) | bestätigt |

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
