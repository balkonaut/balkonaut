# Neuigkeiten

Was sich in Balkonaut geändert hat, die neueste Änderung oben. Docker-App (`:latest`) und
Home-Assistant-Integration (über HACS) bekommen Neuerungen mit der nächsten Version.
Vorabversionen (Beta) zeigt HACS nur, wenn bei Balkonaut die Entität *Vorabversion* eingeschaltet ist.
Was noch kommt, steht unter [Geplant](geplant.md).

## 1.0.3 · 12.11.2026

Fasst die Vorabversionen 1.0.3-beta.1 und beta.2 zusammen (Einzelheiten weiter unten): Warnung *Ungleich* misst
an der eigenen Anlage, Übersicht und Status antworten auch nach längerer Pause sofort.

**Neu seit beta.2: Docker-App**

- Eigenes Repository [balkonaut-docker](https://github.com/balkonaut/balkonaut-docker) und neuer Image-Name
  `ghcr.io/balkonaut/balkonaut-docker`. Das alte Image `ghcr.io/balkonaut/balkonaut` bekommt keine Updates mehr,
  bitte in der `docker-compose.yml` umstellen ([Docker-App](docker.md#installation-mit-dem-fertigen-image)).
- Neue Images gibt es nur noch mit einer neuen Version, nicht mehr nach jeder Änderung.

## 1.0.3-beta.2 · 08.11.2026 (Vorabversion)

**Docker-App und Home-Assistant-Integration**

- Warnung *Ungleich*: Tage, an denen die Prognose anders auf die Flächen verteilt war (etwa vor einer Änderung der
  Flächen oder Prognose-Entitäten), zählen nicht mehr zum üblichen Verhältnis; sonst konnte die Warnung danach
  fälschlich erscheinen (08.11.2026)

## 1.0.3-beta.1 · 08.11.2026 (Vorabversion)

**Docker-App und Home-Assistant-Integration**

- Warnung *Ungleich*: vergleicht mit dem für die eigene Anlage üblichen Verhältnis der beiden Wechselrichter statt
  mit fester Schwelle. Flächen mit verschiedener Ausrichtung oder Modulzahl lösen sie nicht mehr aus, nur noch eine
  Veränderung; sie erscheint frühestens nach 14 vergleichbaren Tagen. Tage mit vollem Akku zählen für den
  Speicher-Wechselrichter nicht mehr, siehe [Warnungen](auswertung.md#warnungen) (08.11.2026)
- Übersicht und Status antworten auch beim ersten Aufruf nach längerer Pause sofort; bisher las jeder Aufruf alle
  Rohwerte der letzten 14 Tage (04.11.2026)

## 1.0.2 · 04.11.2026

Fasst die Vorabversionen 1.0.2-beta.1 bis beta.7 zusammen (Einzelheiten weiter unten). Das Add-on gibt es nicht
mehr: Balkonaut läuft als Docker-App oder als Home-Assistant-Integration (siehe [Installation](index.md)).

**Neu seit beta.7**

- Tag, Monat und Jahr beginnen in der Zeitzone von Home Assistant statt fest in `Europe/Berlin`; die Docker-App nimmt
  die Variable `TZ` (Vorgabe `Europe/Berlin`), siehe [Docker-App](docker.md)
- Verlauf, Diagramm *Akku*: feinere Hilfslinien (Ladestand alle 20 %, kWh mit runden Werten), schmalere Balken
- Alle Balkendiagramme: Balken mit leicht gerundeten Ecken am Ende

**Home-Assistant-Integration**

- Geräte direkt per Adresse, ohne die Integrationen der Hersteller: APsystems EZHI, Shelly (Pro 3EM, EM, Plug),
  OpenDTU, AhoyDTU, Victron GX (MQTT oder Modbus TCP) und Deye; OpenDTU, AhoyDTU, Victron und Deye nur gegen einen
  Nachbau getestet. Zugeordnete Entitäten gehen vor, nicht erreichbare Geräte melden sich als Reparaturhinweis
- Die Betriebsart *Mit einer Balkonaut-App* entfällt, ein solcher Eintrag meldet sich als Reparaturhinweis; den
  Verlauf einer Docker-App übernimmt weiterhin die Aktion *Aus Balkonaut-App übernehmen*
- Einrichtung beginnt direkt ohne Auswahlmenü, *Geräte direkt abfragen* steht in Schritt 2 oben, aktuelle Werte bei
  *Vorzeichen drehen*
- Neue optionale Messgröße *Betriebsart (Szenario)*, beim APsystems EZHI automatisch zugeordnet
- Karte holt ihre Werte alle 10 Sekunden selbst, Panel mit Kachel *Einrichtung*, solange etwas fehlt
- Tagesprognose aus Flächen: ein Abruf je Fläche zur vollen und halben Stunde; für Wechselrichter mit
  Prognose-Entität kein eigener Abruf

**Docker-App**

- [APsystems-Cloud (optional)](einstellungen.md#apsystems-cloud-optional) für den APsystems EZHI: Szenario,
  Ladegrenzen, Entladeschutz und Ein/Aus lesen und setzen. Ab Werk aus, nicht offiziell, Nutzung auf eigenes Risiko
- Geräte direkt: dazu Victron GX und Deye (nur gegen einen Nachbau getestet)
- Akku-Werte von Hand eintragen, wenn das Gerät sie nicht liefert (Einstellungen, Kachel *Akku*)
- Übersicht aktualisiert sich alle 10 Sekunden ohne Neuladen
- Formulare nur von der eigenen Seite, `config.yaml` nur für den Besitzer lesbar

**Docker-App und Home-Assistant-Integration (Karte und Panel)**

- Energiefluss mit leuchtendem Schweif und runden Ecken, gestauchten langen Namen, bei Victron über MQTT je
  Laderegler ein Solarfeld
- Neue Kacheln *Energiewege*, *Autarkie heute* und *Weiteres Akku-Modul*; alle Kacheln einheitlich mit Erklärung
  (Knopf *i*) und Bewertung von rot bis grün; Szenario unter den Grenzwerten des Akkus
- Diagramm *Woher kommt dein Strom*: Balkonkraftwerk und Netz nebeneinander, feinere Skala, erwartete Erzeugung als
  Linie; neues Diagramm *Akku* mit Ladestand, Laden und Entladen
- Nulleinspeisung: Karte *Nach Uhrzeit*; Monatsbericht: ein Klick auf einen Tag öffnet ihn im Verlauf
- Akku: Kapazität und Ladegrenzen als letzter bekannter Wert, Wirkungsgrad mit dem Ladestand vom Beginn des Zeitraums
- Handy: breite Kacheln passen in die Zeile, Überschriften mit Silbentrennung

**Korrekturen**

- Regelgüte und Ertragswächter rechnen Tage der Zeitumstellung richtig (23 bzw. 25 Stunden)
- Statusberechnung deutlich schneller bei langer Historie, Übernahme des Verlaufs braucht viel weniger Speicher
- Panel: beim schnellen Wechsel der Tabs erscheint nicht mehr der falsche Inhalt
- MQTT-Abfrage mit Zeit- und Größengrenze

## 1.0.2-beta.7 · 03.11.2026 (Vorabversion)

**Docker-App**

- [APsystems-Cloud (optional)](einstellungen.md#apsystems-cloud-optional) für den APsystems EZHI: liest alle 5 Minuten
  Szenario, Ein/Aus, Ladegrenzen, Entladeschutz und Abgabelimit und kann Szenario, Ladegrenzen, Entladeschutz und
  Ein/Aus setzen. Ab Werk aus, nicht offiziell, Nutzung auf eigenes Risiko. Knöpfe zeigen grün, wenn ein Wert
  übernommen ist (02.11.2026)
- Kachel *Akku*: Abschnitt *Szenario* unter den Grenzwerten (02.11.2026)
- Formulare nimmt die App nur noch von der eigenen Seite an, `config.yaml` ist nur für den Besitzer lesbar (02.11.2026)
- Energiefluss: statt wandernder Pfeile ein leuchtender Schweif, der nach hinten ausblendet, Leitungen mit runden Ecken (03.11.2026)

**Home-Assistant-Integration**

- Neue optionale Messgröße *Betriebsart (Szenario)*: Karte und Panel zeigen das Szenario des Speichers unter den
  Grenzwerten des Akkus, beim APsystems EZHI aus der Integration *APsystems EZHI Local API* automatisch zugeordnet
  (02.11.2026)
- Karte, Energiefluss: statt wandernder Pfeile ein leuchtender Schweif, der nach hinten ausblendet, Leitungen mit runden Ecken (03.11.2026)

## 1.0.2-beta.6 · 01.11.2026 (Vorabversion)

- Die Betriebsart *Mit einer Balkonaut-App* entfällt: Die Home-Assistant-Integration misst immer selbst. Ein solcher Eintrag startet nicht mehr und meldet sich als Reparaturhinweis; den Verlauf einer Docker-App übernimmt weiterhin die Aktion *Aus Balkonaut-App übernehmen*
- Einrichtung: Schritt 1 erklärt, wann er leer bleibt; in Schritt 2 steht *Geräte direkt abfragen* ganz oben, die aktuellen Werte stehen bei *Vorzeichen drehen*; die Einrichtung beginnt direkt ohne Auswahlmenü
- Geräte direkt per Adresse: Victron GX (MQTT oder Modbus TCP) und Deye (Hybrid einphasig über den Logger-Stick, Mikrowechselrichter über die Statusseite), beide nur gegen einen Nachbau getestet
- Energiefluss: bei Victron über MQTT je Laderegler ein eigenes Solarfeld
- Verlauf: neues Diagramm *Akku* mit Ladestand als Linie, Laden nach oben und Entladen nach unten
- Handy: die breite Kachel *Weiteres Akku-Modul* passt in die Zeile, Überschriften mit Silbentrennung
- MQTT-Abfrage mit Zeit- und Größengrenze

## 1.0.2-beta.5 · 27.10.2026 (Vorabversion)

- Geräte direkt per Adresse: In Schritt 2 der Einrichtung lassen sich APsystems EZHI, Shelly (Pro 3EM, EM, Plug), OpenDTU und AhoyDTU per IP-Adresse eintragen, ganz ohne deren Integrationen; zugeordnete Entitäten gehen vor, nicht erreichbare Geräte melden sich als Reparaturhinweis
- Tagesprognose: Für Wechselrichter mit Prognose-Entität ruft Balkonaut Forecast.Solar nicht mehr selbst ab
- Nulleinspeisung: Karte *Nach Uhrzeit* mit Anteil nahe 0 W und vermeidbarem Netzbezug je Stunde
- Energiefluss mit wandernden Pfeilen, lange Namen werden gestaucht
- Kachel *Autarkie heute* (Autarkie und Eigenverbrauchsquote als Ringe)
- Kachel *Weiteres Akku-Modul*: was ein zusätzliches Modul im Jahr höchstens bringen würde
- Akku: Kapazität und Ladegrenzen als letzter bekannter Wert, EZHI liefert die Kapazität direkt; Wirkungsgrad mit dem Ladestand vom Beginn des Zeitraums, über 100 % als –
- Monatsbericht: ein Klick auf einen Tag öffnet ihn im Verlauf
- Diagramme mit feinerer Skala und blassen Zwischenlinien
- Startseite: *Woher kommt dein Strom heute?* und *Energiewege* stehen jetzt über der Bilanz

Aus den vorigen Betas: Diagramm mit Prognoselinie, einheitliche Kacheln, Kachel *Einrichtung*, Kacheln mit Erklärung und Bewertung, *Energiewege*, Karte mit eigenem Abruf, schnellere Statusberechnung, sparsamere Übernahme des Verlaufs.

## 1.0.2-beta.4 · 25.10.2026 (Vorabversion)

- Diagramm *Woher kommt dein Strom*: Balkonkraftwerk und Netz nebeneinander, feinere Skala, erwartete Erzeugung je Stunde als gestrichelte Linie (aus der Forecast.Solar-Integration oder den Flächen), Knopf *i* mit Erklärung
- Kacheln einheitlich in Übersicht, Verlauf, Nulleinspeisung und Bericht: Werte, Bewertung und Farbskala einer Reihe auf einer Linie
- Prognose aus Flächen: ein Abruf je Fläche zur vollen und halben Stunde liefert Tages- und Stundenwerte; nach Fehlern erst zum nächsten Zeitpunkt (Forecast.Solar erlaubt 12 Abrufe je Stunde und IP-Adresse)
- Einrichtung und Konfigurieren: Hinweis, dass die Tagesprognose optional ist
- Monatsbericht ohne die Erwartung laut PVGIS

Aus den vorigen Betas: Kachel *Einrichtung*, Kacheln mit Erklärung und Bewertung, *Energiewege*, Karte mit eigenem Abruf, Status höchstens alle 10 Sekunden frisch, Tage der Zeitumstellung, schnellere Statusberechnung, sparsamere Übernahme des Verlaufs.

## 1.0.2-beta.3 · 25.10.2026 (Vorabversion)

- Panel: Kacheln in Bilanz, Akku und Nulleinspeisung mit Knopf *i* für eine kurze Erklärung
- Panel: Kennzahlen mit klarer Güte (z. B. Nahe 0 W, Reaktionszeit, Wirkungsgrad Akku) mit Skala von rot bis grün und Bewertung gut, mittel oder schwach

Aus 1.0.2-beta.2:
- Panel: Kachel *Einrichtung*, solange Messgrößen, Prognose oder Preise und Anlagekosten fehlen

Aus 1.0.2-beta.1:
- Karte: holt ihre Werte alle 10 Sekunden selbst und bleibt nicht mehr stehen, wenn die App auf dem Handy im Hintergrund war
- Home-Assistant-Integration: Status wird beim Abruf von Karte und Panel frisch berechnet (höchstens alle 10 Sekunden)
- Panel und Docker-App: Kachel *Energiewege*: wohin die Sonnenenergie ging und wie viel der Akku-Entladung im Haus ankam
- Panel: beim schnellen Wechsel der Tabs erscheint nicht mehr der falsche Inhalt
- Regelgüte und Ertragswächter rechnen Tage der Zeitumstellung richtig
- Statusberechnung deutlich schneller bei langer Historie
- Übernahme des Verlaufs aus Home Assistant braucht viel weniger Speicher

## 1.0.2-beta.2 · 25.10.2026 (Vorabversion)

- Panel: Kachel *Einrichtung* oben in der Übersicht, solange Messgrößen, Prognose oder Preise und Anlagekosten fehlen; das Datum der Inbetriebnahme ist als vierter Schritt empfohlen

Aus 1.0.2-beta.1:
- Karte: holt ihre Werte alle 10 Sekunden selbst und bleibt nicht mehr stehen, wenn die App auf dem Handy im Hintergrund war
- Home-Assistant-Integration: Status wird beim Abruf von Karte und Panel frisch berechnet (höchstens alle 10 Sekunden)
- Panel und Docker-App: neue Kachel *Energiewege*: wohin die Sonnenenergie ging (direkt ins Haus, in den Akku, eingespeist) und wie viel der Akku-Entladung im Haus ankam
- Docker-App und Add-on: Übersicht aktualisiert sich alle 10 Sekunden ohne Neuladen der Seite
- Panel: beim schnellen Wechsel der Tabs erscheint nicht mehr der falsche Inhalt
- Regelgüte und Ertragswächter rechnen Tage der Zeitumstellung richtig (23 bzw. 25 Stunden)
- Statusberechnung deutlich schneller bei langer Historie
- Übernahme des Verlaufs aus Home Assistant braucht viel weniger Speicher

## 1.0.2-beta.1 · 25.10.2026 (Vorabversion)

- Karte: holt ihre Werte alle 10 Sekunden selbst und bleibt nicht mehr stehen, wenn die App auf dem Handy im Hintergrund war
- Home-Assistant-Integration: Status wird beim Abruf von Karte und Panel frisch berechnet (höchstens alle 10 Sekunden)
- Panel und Docker-App: neue Kachel *Energiewege*: wohin die Sonnenenergie ging (direkt ins Haus, in den Akku, eingespeist) und wie viel der Akku-Entladung im Haus ankam
- Docker-App und Add-on: Übersicht aktualisiert sich alle 10 Sekunden ohne Neuladen der Seite
- Panel: beim schnellen Wechsel der Tabs erscheint nicht mehr der falsche Inhalt
- Regelgüte und Ertragswächter rechnen Tage der Zeitumstellung richtig (23 bzw. 25 Stunden)
- Statusberechnung deutlich schneller bei langer Historie
- Übernahme des Verlaufs aus Home Assistant braucht viel weniger Speicher

## 1.0.1 · 24.10.2026

**Prognose ohne Forecast.Solar-Integration**

- Home-Assistant-Integration: unter *Konfigurieren* je eine Fläche am Speicher und am zweiten Wechselrichter (Neigung, Ausrichtung, Leistung). Ist keine Prognose-Entität zugeordnet, ruft Balkonaut die Tagesprognose selbst bei Forecast.Solar ab, mit dem Standort aus Home Assistant, im Hintergrund und höchstens einmal je Stunde
- Add-on: Abschnitt *Standort und Flächen* in den Einstellungen; ohne Breiten- und Längengrad gilt der Standort aus Home Assistant
- Die Einrichtungs-Kachel zählt den Schritt Standort mit Flächen oder einer Prognose-Entität

**Sicherheit**

- Karte und Panel escapen alle Texte und Werte vor der Anzeige; Live-Werte der App werden nur als Zahl übernommen

**Korrekturen**

- Warnung „keine Messwerte“ erscheint auch, wenn nur noch die Prognose ankommt
- Akku-Auswertung: die laufende Stunde gilt nicht mehr fälschlich als „leerer Akku“
- Kein Absturz des Status bei sehr kleiner Ersparnis
- Regelgüte: 0 % Entlademinimum und 0 W Limit gelten wie gemessen
- Übernahme aus der App überschreibt keine eigenen Stunden mehr
- Datenbankzugriffe in der App nacheinander, sauberes Entladen der Home-Assistant-Integration

## 1.0.1-beta.1 · 24.10.2026 (Vorabversion)

- Home-Assistant-Integration: unter *Konfigurieren* je eine Fläche am Speicher und am zweiten Wechselrichter; ohne Forecast.Solar-Integration ruft Balkonaut die Tagesprognose dann selbst ab (Standort aus Home Assistant)
- Add-on/Docker: Abschnitt *Standort und Flächen* auch im Add-on, Prognose aus eingetragenen Flächen
- Karte und Panel: alle Texte werden vor der Anzeige escaped (aus dem HACS-Review)

## 1.0.0 · 24.10.2026

**Einrichtung in der App (Docker und Add-on)**

- Kachel *Einrichtung* oben auf der Übersicht mit drei Schritten (Geräte, Standort und Flächen, Preise), Fortschritt und hervorgehobenem nächsten Schritt; verschwindet, sobald alles erledigt ist. Im Add-on gelten die Entitäten und die Tagesprognose aus dessen Konfiguration
- Standort per Adresssuche (OpenStreetMap) oder, über HTTPS, per *Meinen Standort verwenden*
- Klarerer Hinweis, welche Geräte direkt erkannt werden (APsystems EZHI, Shelly Pro 3EM, Shelly Plug) und dass andere über die Home-Assistant-Integration laufen
- Der Link zum Datum der Inbetriebnahme springt direkt zum Feld, *Handbuch* öffnet die Website

**Home-Assistant-Integration**

- Die Aktion *Historie aus Balkonaut-App übernehmen* dürfen nur Administratoren ausführen (seit 0.9.3)

## 0.9.3 · 24.10.2026

**Sicherheit**

- Die Aktion *Historie aus Balkonaut-App übernehmen* (`balkonaut.import_from_app`) dürfen nur noch Administratoren ausführen. Sie ruft eine angegebene Adresse ab und überschreibt die gespeicherte Historie.

## 0.9.2 · 23.10.2026

**Energiefluss mit Modulen und Gerätenamen**

- Oben je Wechselrichter ein Modulfeld, ein zweiter Wechselrichter erscheint als eigenes Feld zwischen seinen Modulen und dem Speicher
- Die Mitte trägt das Modell des Wechselrichters aus dem Geräteregister von Home Assistant (z. B. EZHI), ohne bekanntes Modell Wechselrichter
- Der zweite Wechselrichter trägt sein Modell, wenn er in Home Assistant ein eigenes Gerät ist, sonst die eingetragene Bezeichnung
- Neue optionale Felder unter *Konfigurieren*: Bezeichnung des Akkus (z. B. der Hersteller) und des zusätzlichen Wechselrichters (z. B. EZ1-M)
- Die Warnung bei fehlenden Messwerten nennt Geräte oder Home Assistant

## 0.9.1 · 23.10.2026

**Vorbereitung für die HACS-Standardliste**

- HACS-Prüfung läuft ohne Ausnahme, das Logo liegt im Ordner brand der Home-Assistant-Integration
- Link zum Unterstützen über Buy Me a Coffee in README, Handbuch und GitHub (Sponsor-Knopf)
- Handbuch: eigene Seite [Unterstützte Geräte](https://balkonaut.github.io/balkonaut/geraete/) mit Prüfstand je Gerät

## 0.9.0 · 23.10.2026

**Noch mehr Hersteller in der geführten Einrichtung**

Neu vorbelegt, samt Vorzeichen, wo es in Code oder Doku der Integration belegt ist:
- **Anker Solix** Solarbank
- **Zendure** SolarFlow, Hyper, AIO
- **EcoFlow** PowerStream, STREAM, Smart Plug
- **Growatt** MIN, MIC, MOD, SPH (Growatt in Home Assistant)
- **Victron** GX über Victron GX, Victron MQTT oder Victron Modbus
- **Fox ESS** über FoxESS Modbus oder FoxESS Cloud
- **Marstek** Venus über Modbus oder lokale API
- **Sungrow** über die Modbus-Vorlage von mkaiser; Entitäten ohne Gerät schlägt die Einrichtung jetzt ebenfalls vor, wenn ein Profil sie genau kennt
- **SolaX** über SolaX Modbus
- Netzmessung über **Shelly Pro EM** und **Tibber Pulse**

Alle diese Profile sind aus dem Quellcode der jeweiligen Integration abgeleitet und noch nicht an echten Geräten bestätigt. Rückmeldungen bitte als Issue mit der Diagnose-Datei, siehe [Gerät melden](https://balkonaut.github.io/balkonaut/installation/#gerat-melden).

## 0.8.0 · 23.10.2026

**Weitere Hersteller in der geführten Einrichtung**

Die Einrichtung belegt die Entitäten jetzt auch für diese Geräte vor, samt Vorzeichen, wo es feststeht:
- **Deye** (Hybrid und Mikrowechselrichter) über Solarman, beide verbreiteten Integrationen
- **Huawei** SUN2000 mit LUNA2000 und Power Meter über Huawei Solar
- **Hoymiles** HM/HMS über OpenDTU, AhoyDTU oder Hoymiles WiFi

Diese Profile sind aus dem Quellcode der jeweiligen Integration abgeleitet und noch nicht an echten Geräten bestätigt. Rückmeldungen bitte als Issue mit der Diagnose-Datei (*⋮ → Diagnose herunterladen*), siehe [Gerät melden](https://balkonaut.github.io/balkonaut/installation/#gerat-melden).

## 0.7.1 · 23.10.2026

**Handbuch als Website**

- Das Handbuch steht jetzt unter https://balkonaut.github.io/balkonaut/ und wird bei jeder Änderung neu veröffentlicht
- Der Knopf *Handbuch* im Panel und der Link *Dokumentation* der Home-Assistant-Integration führen dorthin

## 0.7.0 · 23.10.2026

**Reparaturhinweis bei fehlender Entität**

- Gibt es eine zugeordnete Entität nicht mehr oder ist sie deaktiviert, etwa weil die Integration des Geräts sie umbenannt hat, erscheint unter *Einstellungen → Reparaturen* ein Hinweis mit den betroffenen Entitäten und einem Link zu Balkonaut; dort über *Neu konfigurieren* neu zuordnen
- Kurz nicht verfügbare Entitäten (Neustart, WLAN) lösen keinen Hinweis aus
- Der Hinweis verschwindet von selbst, sobald alle Entitäten wieder da sind

## 0.6.1 · 23.10.2026

**Korrekturen an der geführten Einrichtung**

- Prognose wieder mit der normalen Entitätsauswahl; die Ausrichtung der Forecast.Solar-Flächen steht bei den aktuellen Werten, z. B. „Prognose Speicher: 4,2 kWh (Südost 150°)“
- Zahlen mit Dezimalkomma
- Keine doppelte Richtungsangabe bei „Abgabe ins Haus“

## 0.6.0 · 23.10.2026

**Geführte Einrichtung**

Im eigenständigen Betrieb muss man die Namen der Entitäten nicht mehr kennen:
- Geräte wählen: Netzmessung, Speicher oder Wechselrichter, zusätzlicher Wechselrichter, Messung am Einspeisepunkt
- Balkonaut schlägt die Entitäten vor, für APsystems EZHI und EZ1-M, Shelly Pro 3EM und Shelly Plug genau samt Vorzeichen, bei anderen Geräten nach Art und Einheit, wenn das eindeutig ist
- Aktuelle Werte mit Richtung zur Kontrolle, z. B. „Netzleistung: 312 W (Bezug)“
- Prognosen von Forecast.Solar heißen nach der Ausrichtung ihrer Flächen, z. B. „Südost 135°“
- Zusammenfassung, welche Funktionen mit der Zuordnung verfügbar sind und welche nicht

**Neu konfigurieren**

- Zuordnung der Entitäten oder Adresse der App nachträglich ändern über *⋮ → Neu konfigurieren*, Eintrag und Messdaten bleiben erhalten

## 0.5.0 · 22.10.2026

**Umzug aus der Docker-Installation oder dem Add-on**

Wer Balkonaut bisher als Docker-Container (z. B. auf einer NAS) oder als Home-Assistant-Add-on betrieben hat, kann dessen gespeicherte Messdaten jetzt in die eigenständige Home-Assistant-Integration übernehmen:
- Neue Aktion *Balkonaut: Historie aus Balkonaut-App übernehmen* (`balkonaut.import_from_app`) mit der Adresse des laufenden Containers bzw. Add-ons, z. B. `http://192.168.1.10:8000`
- Stunden vor der ersten eigenen Messung der Home-Assistant-Integration werden durch die genaueren Werte aus dem Container ersetzt, eigene Messungen bleiben
- Der Container braucht dafür die neue Schnittstelle `/api/v1/export`: vorher das Docker-Image aktualisieren (`docker compose up -d` bzw. neu bauen)
- Danach kann der Container abgeschaltet werden

**Korrekturen**

- Ertragswächter vergleicht nur Tage, für die es eine Prognose gibt; eine junge Prognose verzerrt die Quote nicht mehr
- Überschrift „Woher kommt dein Strom heute?“ in Übersicht und Panel

## 0.4.0 · 22.10.2026

**Panel „Balkonaut“ in der Seitenleiste**

- Erscheint automatisch, sobald ein Balkonaut-Eintrag eingerichtet ist, in beiden Betriebsarten
- Übersicht mit Energiefluss-Karte, Warnungen, Bilanz (heute, Monat, Jahr, gesamt), Akku, heutigem Verlauf und Amortisation
- Verlauf (Tag, Woche, Monat, Jahr), Nulleinspeisung (Regelgüte der letzten 7 Tage) und Monatsbericht zum Drucken
- Einstellungen führen zu den Optionen der Home-Assistant-Integration

**Karte**

- Ruhende Leitungen besser sichtbar, volle Breite in der Abschnittsansicht, Energiefluss höchstens 520 px breit

**Home-Assistant-Integration**

- WebSocket-Befehle `balkonaut/verlauf`, `balkonaut/bericht`, `balkonaut/nulleinspeisung`
- Im eigenständigen Betrieb wird die Regelgüte abgeschlossener Tage stündlich für den Monatsbericht gesichert

## 0.3.1 · 22.10.2026

- Logo der Home-Assistant-Integration (eigene Marken-Bilder im Ordner `brand`, ab HA 2026.10)

## 0.3.0 · 22.10.2026

**Lovelace-Karte**

- Neue Karte `custom:balkonaut-card` mit Energiefluss (beide Wechselrichter, Leitungsstärke und Tempo nach Leistung), Akku-Ring mit SoC-Grenzen, Ampel-Farbe und Restzeit sowie Ersparnis und Autarkie von heute
- Wird von der Home-Assistant-Integration automatisch geladen, kein Eintrag unter *Ressourcen* nötig; im Dashboard unter *Karte hinzufügen → Balkonaut*
- Im eigenständigen Betrieb live aus den zugeordneten Entitäten, passt sich hellem und dunklem Theme an

**Home-Assistant-Integration**

- WebSocket-Befehl `balkonaut/status` als Datenquelle für Karte und künftiges Panel

## 0.2.1 · 22.10.2026

**Home-Assistant-Integration, eigenständiger Betrieb**

- Beim ersten Start übernimmt Balkonaut einmalig den Verlauf der zugeordneten Entitäten aus dem Recorder (standardmäßig 10 Tage), die Auswertung beginnt nicht mehr bei null
- Erzeugung zählt nur noch positive Anteile: ein Verbraucher am Off-Grid-Port oder Standby-Bezug ergibt keine negative Erzeugung mehr

## 0.2.0 · 22.10.2026

**Home-Assistant-Integration: eigenständiger Betrieb**

- Neue Betriebsart *Eigenständig in Home Assistant*: Entitäten je Messgröße zuordnen, Balkonaut misst alle 10 s selbst, speichert in `balkonaut/balkonaut.db` im Konfigurationsordner und rechnet Bilanz, Akku und Amortisation ohne Docker-App oder Add-on
- Vorzeichen je Messgröße drehbar (z. B. Abgabe ins Haus beim APsystems EZHI)
- Arbeitspreis, Einspeisevergütung, Anschaffungskosten und Inbetriebnahme unter *Konfigurieren*
- Bestehende Einrichtungen mit Adresse einer Balkonaut-App laufen unverändert weiter
- HACS lädt die Home-Assistant-Integration jetzt als `balkonaut.zip` aus dem Release

**Docker-App und Add-on**

- Neues Design „Leitwarte“ mit Energiefluss, Akku-Ring mit SoC-Grenzen und Restzeit
- Home-Assistant-Add-on mit Oberfläche in der Seitenleiste (Ingress)

Noch nicht im eigenständigen Betrieb: Übernahme des HA-Verlaufs, Weboberfläche (folgen in den nächsten Versionen).

## 0.1.0 · 20.10.2026

Erste öffentliche Version von Balkonaut: Antworten statt Rohdaten für Balkonkraftwerke mit Speicher.

**Docker-App**

- Erfassung über Home Assistant alle 10 s, SQLite mit Stundenwerten, Import des HA-Verlaufs
- Bilanz für heute, Monat, Jahr und gesamt: Erzeugung, Eigenverbrauch, Netzbezug, Einspeisung, Autarkie, Ersparnis
- Amortisation mit Datum der Inbetriebnahme und Jahresverlauf (PVGIS, Flächen aus Forecast.Solar)
- Akku-Auswertung: Vollzyklen, Gesundheit, Wirkungsgrad, Stunden mit vollem oder leerem Akku
- Regelgüte der Nulleinspeisung, Verlaufsansichten, Monatsbericht, Ertragswächter mit Warnungen
- REST-API unter `/api/v1`, Handbuch unter `/handbuch/`

**Home-Assistant-Integration** (HACS, benutzerdefiniertes Repository, Typ *Integration*)
- Einrichtung per Klick, 22 Sensoren, Problem-Sensor und Ereignis für Warnungen
- Diagnose-Download und Reparaturhinweis, wenn die App nicht erreichbar ist

Getestet mit Home Assistant 2026.10, APsystems EZHI und EZ1-M, Shelly Pro 3EM.
