"""Direkte Geräte-Adapter: liest Geräte im Heimnetz ohne Home Assistant, lokal per HTTP ohne Anmeldung.

Liefert dieselben Messgrößen wie der Home-Assistant-Adapter (W, kWh, Vorzeichen siehe dort).
Geprüft an APsystems EZHI, Shelly Pro 3EM und Shelly Outdoor Plug S Gen3 (Oktober 2026). Shelly mit einer Phase
(EM1) ist aus der Dokumentation abgeleitet, nicht an Geräten geprüft. OpenDTU und AhoyDTU (Quellcode) sowie Victron GX
(MQTT, Modbus TCP, Dokumentation von Victron) sind nur gegen die Nachbauten in tools/victron-mock geprüft. Deye
(Statusseite des Sticks, Solarman V5 nach pysolarmanv5, Register nach ha-solarman) ebenso nur gegen einen Nachbau.
"""
import base64
import functools
import json
import logging
import random
import re
import socket
import struct
import time
import urllib.error
import urllib.request

from . import forecast

log = logging.getLogger(__name__)


def _get(host, path, timeout=5):
    with urllib.request.urlopen(f"http://{host}/{path}", timeout=timeout) as r:
        return json.load(r)


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@functools.lru_cache
def _ezhi_capacity(host):
    """Akku-Kapazität in kWh, einmal je Start. Vereinfachung: ein weiteres Modul zeigt sich erst nach einem Neustart."""
    return _num((_get(host, "getDeviceInfo").get("data") or {}).get("batteryCapacity"))


def apsystems_ezhi(host):
    """APsystems EZHI, lokale API (in der APsystems-App den lokalen Modus aktivieren)."""
    d = _get(host, "getOutputData").get("data") or {}
    og = _num(d.get("ogP"))
    return {
        "pv_power": _num(d.get("pvP")),
        "pv_energy": _num(d.get("pvTE")),
        "pv_ac_power": _num(d.get("ofgP")),  # Off-Grid-Port, z. B. ein EZ1-M
        "battery_power": _num(d.get("batP")),  # + Laden
        "battery_soc": _num(d.get("batSoc")),
        "battery_soh": _num(d.get("batSoh")),
        "battery_capacity": _ezhi_capacity(host),
        "battery_charge_energy": _num(d.get("batCTE")),
        "battery_discharge_energy": _num(d.get("batDTE")),
        "output_power": None if og is None else 0.0 - og,  # EZHI: negativ bei Abgabe ins Haus; 0.0 - og ohne -0,0
        # ogOTE und ofgITE liefert die Firmware unsinnig (z. B. 1,1e14), daher nicht verwendet
    }


def shelly_em(host):
    """Shelly Pro 3EM: Netzleistung über alle Phasen saldiert, + Bezug."""
    return {"grid_power": _num(_get(host, "rpc/EM.GetStatus?id=0").get("total_act_power"))}


def shelly_em1(host):
    """Shelly mit Messkanal EM1, z. B. Pro EM oder EM Gen3: Netzleistung am ersten Kanal (nicht geprüft)."""
    return {"grid_power": _num(_get(host, "rpc/EM1.GetStatus?id=0").get("act_power"))}


def opendtu(host):
    """Hoymiles über OpenDTU: Leistung und Zähler aller Wechselrichter zusammen (nicht geprüft). Ohne Speicher ist
    das die Erzeugung und zugleich die Abgabe ins Haus."""
    total = _get(host, "api/livedata/status").get("total") or {}
    power, energy = _num((total.get("Power") or {}).get("v")), _num((total.get("YieldTotal") or {}).get("v"))
    return {"pv_power": power, "pv_energy": energy, "output_power": power, "output_energy": energy}


def ahoydtu(host):
    """Hoymiles über AhoyDTU: Leistung aller Wechselrichter zusammen, ohne Zähler (nicht geprüft)."""
    powers = [p for i in _get(host, "api/index").get("inverter") or [] if (p := _num(i.get("cur_pwr"))) is not None]
    power = sum(powers) if powers else None
    return {"pv_power": power, "output_power": power}


def shelly_plug(host):
    """Shelly Plug (Gen2, Gen3) am Einspeisepunkt: Abgabe ins Haus mit Zähler."""
    s = _get(host, "rpc/Switch.GetStatus?id=0")
    wh = _num((s.get("aenergy") or {}).get("total"))
    return {"output_power": _num(s.get("apower")), "output_energy": None if wh is None else wh / 1000}


def deye_micro(host):
    """Deye-Mikrowechselrichter mit WLAN-Stick (z. B. SUN600/800 G3): Statusseite des Sticks (nicht geprüft). Nachts ist
    der Stick aus. Vereinfachung: Anmeldung fest mit der Werkseinstellung admin/admin."""
    auth = {"Authorization": "Basic " + base64.b64encode(b"admin:admin").decode()}
    with urllib.request.urlopen(urllib.request.Request(f"http://{host}/status.html", headers=auth), timeout=5) as r:
        web = dict(re.findall(r'webdata_(\w+)\s*=\s*"([^"]*)"', r.read(65536).decode(errors="replace")))
    if "now_p" not in web:
        raise ValueError("keine Statusseite eines Deye-Sticks")
    power, energy = _num(web["now_p"]), _num(web.get("total_e"))
    return {"pv_power": power, "pv_energy": energy, "output_power": power, "output_energy": energy}


def _crc16(data):
    """Prüfsumme eines Modbus-RTU-Rahmens."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = crc >> 1 ^ 0xA001 if crc & 1 else crc >> 1
    return crc


@functools.lru_cache
def _logger_serial(host):
    """Seriennummer des Logger-Sticks, die Solarman V5 in jeder Anfrage braucht, per UDP-Suche (Antwort IP,MAC,Serie)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(3)
        s.sendto(b"WIFIKIT-214028-READ", (host.partition(":")[0], 48899))
        return int(s.recv(256).decode().split(",")[2])


def _solarman(host, start, count):
    """Holding-Register über den Logger-Stick lesen: Modbus RTU (Gerät 1, Funktion 3) in einem Solarman-V5-Rahmen,
    TCP 8899 (host darf einen Port tragen)."""
    rtu = struct.pack(">BBHH", 1, 3, start, count)
    rtu += struct.pack("<H", _crc16(rtu))
    body = struct.pack("<BHIII", 2, 0, 0, 0, 0) + rtu  # Rahmentyp, Sensortyp, drei Zeiten
    frame = struct.pack("<BHHHI", 0xA5, len(body), 0x4510, random.randrange(65536), _logger_serial(host)) + body
    frame += bytes([sum(frame[1:]) & 0xFF, 0x15])
    with _connect(host, 8899) as s:
        s.sendall(frame)
        head = _recv(s, 11)
        if head[0] != 0xA5 or head[3:5] != b"\x10\x15":
            raise ValueError("keine Solarman-V5-Antwort")
        rtu = _recv(s, struct.unpack("<H", head[1:3])[0] + 2)[14:-2]  # Rahmentyp, Status, drei Zeiten; Prüfsumme, Ende
    if len(rtu) < 3 or rtu[1] & 0x80 or rtu[2] < 2 * count:
        raise ValueError(f"Modbus-Fehler bei Register {start}")
    return struct.unpack(f">{count}H", rtu[3:3 + 2 * count])


def _deye_single_phase_hybrid(host):
    """Erkennung: Gerätetyp in Register 0, 3 bzw. 0x300 ist ein einphasiger Hybrid (Lookup in ha-solarman)."""
    if _solarman(host, 0, 1)[0] not in (0x0003, 0x0300):
        raise ValueError("kein einphasiger Deye-Hybrid")


DEYE_FIRST, DEYE_COUNT = 72, 119  # Register 72 bis 190 in einer Anfrage (Modbus erlaubt bis 125)


def deye_hybrid(host):
    """Deye-Hybrid einphasig (SUN-*-SG0xLP1) über den Logger-Stick (nicht geprüft). Register nach deye_hybrid.yaml in
    ha-solarman: Akku 190 positiv beim Entladen, Netz 169 positiv beim Bezug, Zähler in 0,1 kWh, niedriges Wort zuerst.
    Vereinfachung: dreiphasige Hybride (andere Register) und die Kapazität (Register in Ah) fehlen."""
    regs = _solarman(host, DEYE_FIRST, DEYE_COUNT)
    u16 = lambda n: regs[n - DEYE_FIRST]
    s16 = lambda n: u16(n) - 65536 if u16(n) > 32767 else u16(n)
    kwh = lambda n: (u16(n) | u16(n + 1) << 16) / 10
    return {"pv_power": float(sum(u16(n) for n in range(186, 190))), "pv_energy": kwh(96),
            "battery_power": 0.0 - s16(190), "battery_soc": float(u16(184)),
            "battery_charge_energy": kwh(72), "battery_discharge_energy": kwh(74),
            "grid_power": float(s16(169)), "output_power": float(s16(175))}


# Victron GX: Messgröße -> Pfade in com.victronenergy.system, summiert; Akku + Laden, Netz + Bezug wie in Balkonaut
VICTRON = {
    "pv_power": ["/Dc/Pv/Power"],  # Laderegler (DC-gekoppelt)
    "pv_ac_power": [f"/Ac/PvOn{w}/L{n}/Power" for w in ("Output", "Grid") for n in (1, 2, 3)],  # AC-gekoppelt
    "battery_power": ["/Dc/Battery/Power"],
    "battery_soc": ["/Dc/Battery/Soc"],
    "grid_power": [f"/Ac/Grid/L{n}/Power" for n in (1, 2, 3)],
}
VICTRON_HOUSE = [f"/Ac/Consumption/L{n}/Power" for n in (1, 2, 3)]  # Verbrauch im Haus
# Register laut CCGX-Modbus-TCP-register-list-3.81, Unit-ID 100, Faktor 1
VICTRON_REGISTERS = ({f"/Ac/PvOn{w}/L{n}/Power": r + n for w, r in (("Output", 807), ("Grid", 810)) for n in (1, 2, 3)}
                     | {f"/Ac/Consumption/L{n}/Power": 816 + n for n in (1, 2, 3)}
                     | {f"/Ac/Grid/L{n}/Power": 819 + n for n in (1, 2, 3)}
                     | {"/Dc/Battery/Power": 842, "/Dc/Battery/Soc": 843, "/Dc/Pv/Power": 850})
# Blöcke ohne Lücken, sonst lehnt der GX die ganze Anfrage ab
VICTRON_BLOCKS = [(808, 15), (842, 2), (850, 1)]


def _victron(paths):
    def total(wanted):
        found = [v for p in wanted if (v := _num(paths.get(p))) is not None]
        return sum(found) if found else None
    out = {key: total(wanted) for key, wanted in VICTRON.items()}
    # Abgabe ins Haus (PV und Akku zusammen) = Verbrauch minus Netzbezug, daraus entsteht der Hausverbrauch
    house = total(VICTRON_HOUSE)
    out["output_power"] = None if house is None or out["grid_power"] is None else house - out["grid_power"]
    return out


def _connect(host, port, timeout=5):
    """TCP-Verbindung; host darf einen Port tragen, z. B. 192.168.1.30:1502 für einen Mock."""
    name, _, own = host.partition(":")
    return socket.create_connection((name, int(own or port)), timeout=timeout)


def _recv(sock, n):
    data = b""
    while len(data) < n:
        if not (chunk := sock.recv(n - len(data))):
            raise OSError("Verbindung beendet")
        data += chunk
    return data


def _modbus(sock, start, count, unit=100):
    """Holding-Register lesen (Funktion 3). Vereinfachung: alle als int16, uint16 über 32767 W kommt am Balkon nicht vor."""
    sock.sendall(struct.pack(">HHHBBHH", start, 0, 6, unit, 3, start, count))
    head = _recv(sock, 9)  # Transaktion, Protokoll, Länge, Unit, Funktion, Bytes bzw. Fehlercode
    if head[7] & 0x80:
        raise ValueError(f"Modbus-Fehler {head[8]} bei Register {start}")
    return struct.unpack(f">{count}h", _recv(sock, head[8]))


def victron_modbus(host):
    """Victron GX über Modbus TCP (am GX unter Einstellungen, Dienste, Modbus TCP einschalten; nicht geprüft)."""
    regs = {}
    with _connect(host, 502) as s:
        for start, count in VICTRON_BLOCKS:
            regs.update(zip(range(start, start + count), _modbus(s, start, count)))
    return _victron({p: regs[r] for p, r in VICTRON_REGISTERS.items()})


def _str(text):
    return struct.pack(">H", len(text.encode())) + text.encode()


def _packet(kind, body):
    head, n = bytearray([kind]), len(body)
    while True:  # Restlänge als Varint
        head.append(n % 128 | (128 if n >= 128 else 0))
        n //= 128
        if not n:
            return bytes(head) + body


def _mqtt(host, topics, until, publish=None, timeout=5):
    """MQTT 3.1.1 ohne Bibliothek: topics abonnieren, nach dem SUBACK publish (Topic, Nutzlast) senden und
    Nachrichten {Topic: Nutzlast} sammeln, bis until(topic) zutrifft. Höchstens timeout Sekunden insgesamt, auch wenn
    der Broker ständig sendet, und höchstens 64 KiB je Nachricht (Werte des GX sind wenige Bytes)."""
    got, deadline = {}, time.monotonic() + timeout
    with _connect(host, 1883, timeout) as s:
        s.sendall(_packet(0x10, _str("MQTT") + bytes([4, 2]) + struct.pack(">H", 30) + _str("")))  # Client-ID vergibt der Broker
        s.sendall(_packet(0x82, b"\0\1" + b"".join(_str(t) + b"\0" for t in topics)))
        while True:
            kind, n, shift = _recv(s, 1)[0], 0, 0
            while (b := _recv(s, 1)[0]) & 128 and shift < 21:  # Restlänge höchstens 4 Bytes
                n, shift = n | (b & 127) << shift, shift + 7
            if (n := n | b << shift) > 65536 or time.monotonic() > deadline:
                raise OSError("MQTT: Nachricht zu groß oder Zeit überschritten")
            body = _recv(s, n)
            if kind == 0x90 and publish:  # SUBACK
                s.sendall(_packet(0x30, _str(publish[0]) + publish[1]))
            elif kind & 0xF0 == 0x30:  # PUBLISH, QoS 0
                topic = body[2:2 + struct.unpack(">H", body[:2])[0]].decode()
                got[topic] = body[2 + len(topic.encode()):]
                if until(topic):
                    s.sendall(b"\xe0\0")  # DISCONNECT
                    return got


LABELS = {}  # Name je Messgröße, die ein Gerät selbst benennt, z. B. pv_mppt_278_power: "MPPT Südost"


@functools.lru_cache
def _portal_id(host):
    """VRM-Portal-ID aus der Serial-Meldung, die der GX auch ohne Keepalive sendet (wie victron-mqtt). Vereinfachung:
    Abstand der Meldung am echten GX nicht geprüft, 10 s Wartezeit."""
    return next(iter(_mqtt(host, ["N/+/system/0/Serial"], lambda t: True, timeout=10))).split("/")[1]


def victron_mqtt(host):
    """Victron GX über MQTT (am GX unter Einstellungen, Dienste, MQTT einschalten; nicht geprüft). Keepalive löst das
    vollständige Veröffentlichen aus, der GX hält keine Werte vor. Dazu die Leistung je Laderegler (MPPT) als
    pv_mppt_<Instanz>_power mit Namen in LABELS. Vereinfachung: eine Verbindung je Abfrage."""
    pid = _portal_id(host)
    got = _mqtt(host, [f"N/{pid}/system/0/#", f"N/{pid}/full_publish_completed"]
                + [f"N/{pid}/solarcharger/+/{p}" for p in ("Yield/Power", "CustomName", "ProductName")],
                lambda t: t.endswith("/full_publish_completed"), (f"R/{pid}/keepalive", b""))
    vals = {t.split("/", 2)[2]: (json.loads(v) or {}).get("value") for t, v in got.items() if v}
    out = _victron({t.removeprefix("system/0"): v for t, v in vals.items() if t.startswith("system/0/")})
    for t, w in vals.items():
        if t.startswith("solarcharger/") and t.endswith("/Yield/Power"):
            inst = t.split("/")[1]
            out[f"pv_mppt_{inst}_power"] = _num(w)
            LABELS[f"pv_mppt_{inst}_power"] = (vals.get(f"solarcharger/{inst}/CustomName")
                                                or vals.get(f"solarcharger/{inst}/ProductName") or f"Laderegler {inst}")
    return out


# Reihenfolge: spätere Geräte überschreiben frühere, so gilt die Abgabe des Plugs am Einspeisepunkt vor der der DTU,
# die Abgabe-Leistung des Speichers vor der des Plugs, und der Zähler am Einspeisepunkt, den der Speicher nicht
# liefert, bleibt (Handbuch, Messquellen)
TYPES = {"opendtu": opendtu, "ahoydtu": ahoydtu, "deye_micro": deye_micro, "shelly_plug": shelly_plug,
         "apsystems_ezhi": apsystems_ezhi, "deye_hybrid": deye_hybrid,
         "victron_mqtt": victron_mqtt, "victron_modbus": victron_modbus, "shelly_em": shelly_em, "shelly_em1": shelly_em1}
HUB_NAMES = {"apsystems_ezhi": "EZHI", "opendtu": "Hoymiles", "ahoydtu": "Hoymiles", "deye_micro": "Deye",
             "deye_hybrid": "Deye", "victron_mqtt": "Victron",
             "victron_modbus": "Victron"}  # Mitte des Energieflusses

# Erkennung: (Typ, Pfad, Prüfung der Antwort), der erste Treffer gilt
PROBES = [
    ("shelly_plug", "shelly", lambda d: "Plug" in (d.get("app") or "")),  # z. B. PlusPlugS, PlugSG3, OutdoorPlugSG3
    ("shelly_em", "rpc/EM.GetStatus?id=0", lambda d: "total_act_power" in d),  # drei Phasen, z. B. Pro 3EM
    ("shelly_em1", "rpc/EM1.GetStatus?id=0", lambda d: "act_power" in d),  # eine Phase je Kanal, z. B. Pro EM
    ("apsystems_ezhi", "getDeviceInfo", lambda d: (d.get("data") or {}).get("type") == "EZHI"),
    ("opendtu", "api/livedata/status", lambda d: "inverters" in d and "total" in d),
    ("ahoydtu", "api/generic", lambda d: "modules" in d and "esp_type" in d),
]
# ohne JSON-Antwort: Victron GX über Modbus (antwortet sofort), Deye (Hybrid vor Mikrowechselrichter, beide mit
# Stick), zuletzt Victron über MQTT (wartet auf die Serial-Meldung)
SOCKET_PROBES = [("victron_modbus", victron_modbus), ("deye_hybrid", _deye_single_phase_hybrid),
                 ("deye_micro", deye_micro), ("victron_mqtt", _portal_id)]


def detect(host):
    """Gerätetyp unter host erkennen; ValueError, wenn unbekannt."""
    for typ, path, test in PROBES:
        try:
            if test(_get(host, path)):
                return typ
        except (urllib.error.HTTPError, ValueError, AttributeError):  # Gerät antwortet, aber nicht passend
            pass
        except OSError:  # kein Webserver: nicht jede weitere Probe auf die Zeitüberschreitung warten lassen
            break
    for typ, probe in SOCKET_PROBES:
        try:
            probe(host)
            return typ
        except (OSError, ValueError, IndexError):
            pass
    raise ValueError(f"Unter {host} antwortet kein bekanntes Gerät")


class Devices:
    def __init__(self, devices, location=None, planes=()):
        """devices: [{"type": ..., "host": ..., "invert": [Messgrößen]}], location: {"lat": ..., "lon": ...},
        planes: [{"declination": ..., "azimuth": ..., "kwp": ..., "inverter": "storage" | "extra"}]"""
        self.devices = sorted(devices, key=lambda d: list(TYPES).index(d["type"]))
        self.forecast = forecast.Planes(location, planes)
        self.high = {}  # höchster Zählerstand je Messgröße
        self.failures = {}  # Abfragen in Folge ohne Antwort je Adresse

    def read(self):
        """Aktuelle Werte aller Geräte; fehlt ein Gerät, fehlen nur seine Messgrößen."""
        values = {}
        for dev in self.devices:
            try:
                new = TYPES[dev["type"]](dev["host"])
            except (OSError, ValueError) as e:  # nicht erreichbar, Zeitüberschreitung, kein JSON
                log.warning("%s nicht lesbar: %s", dev["host"], e)
                self.failures[dev["host"]] = self.failures.get(dev["host"], 0) + 1
                continue
            self.failures.pop(dev["host"], None)
            for key in dev.get("invert", []):
                if new.get(key) is not None:
                    new[key] = -new[key]
            values.update(new)
        values.update(self.forecast.read())
        for key, value in values.items():
            if key.endswith("_energy") and value is not None:
                # Zähler fallen nie: der EZHI meldet etwa alle 10 h eine Minute lang alle Zähler als 0
                if value <= 0 or value < 0.9 * self.high.get(key, 0):
                    values[key] = None
                else:
                    self.high[key] = max(value, self.high.get(key, 0))
        return values

    def solar_planes(self):
        """Standort und Flächen aus der Konfiguration, für den Jahresverlauf (PVGIS)."""
        return self.forecast.solar_planes()
