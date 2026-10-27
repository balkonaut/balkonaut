"""Mock eines Victron GX (z. B. Cerbo GX) für Tests ohne Gerät: MQTT wie dbus-flashmq und Modbus TCP wie dbus-modbustcp.

Nachgebildet nach github.com/victronenergy/dbus-flashmq (README) und CCGX-Modbus-TCP-register-list-3.81.xlsx:
- MQTT: N/<Portal-ID>/system/0/<Pfad> mit {"value": ...}, nichts retained. R/<Portal-ID>/keepalive veröffentlicht
  alles und meldet N/<Portal-ID>/full_publish_completed; danach Änderungen 60 s lang. Optionen
  "suppress-republish" und "full-publish-completed-echo" wie ab Venus 3.50. Serial alle 5 s auch ohne Keepalive
  (so findet victron-mqtt die Portal-ID; der Abstand am echten GX ist nicht geprüft).
- Modbus TCP: Unit-ID 100 und 0 (System), Funktion 3 und 4, unbekannte Register 0x02, unbekannte Unit-ID 0x0B.
- Zwei Akkus mit 51,2 V parallel (100 Ah und 900 Ah, zusammen 51,2 kWh), je ein Batteriewächter unter battery/<Instanz>.
- Laderegler (MPPT) je Instanz nur über MQTT (solarcharger/<Instanz>/Yield/Power, CustomName, ProductName); über Modbus
  hätten sie eigene, seit Venus 2.60 dynamische Unit-IDs.
Werte wie eine echte Anlage, dauerhaft: Sonne nach Uhrzeit und Jahreszeit, jeden Tag anderes Wetter (sonnig,
wechselhaft, bedeckt) mit Wolken, Hausverbrauch mit Kühlschrank, Kochen, Waschmaschine und Zufall, Akku zwischen 16 und 75 % auf
Nulleinspeisung mit Verzögerung, Rest über das Netz. SPEED lässt die Zeit schneller laufen, WEATHER legt das Wetter fest.
Verlauf: "python gx.py history" im Balkonaut-Image füllt eine leere Datenbank mit den letzten DAYS Tagen.
"""
import asyncio
import json
import math
import os
import random
import struct
import threading
import sys
import time

PORTAL_ID = os.environ.get("PORTAL_ID", "c0619ab00000")
SPEED = float(os.environ.get("SPEED", 1))  # 1 = Echtzeit, 60 = eine Stunde je Minute
DAYS = int(os.environ.get("DAYS", 40))  # Verlauf in Tagen
WEATHER = os.environ.get("WEATHER", "auto")  # auto (jeden Tag anders), sonnig, wechselhaft, bedeckt
PV_AC_WP, BATTERY_W, VOLTAGE = 870, 800, 51.2
# Akkus parallel am DC-Bus, je ein Batteriewächter (com.victronenergy.battery): Instanz, Name, Ah bei 51,2 V
BATTERIES = [(512, "Akku 1", 100), (513, "Akku 2", 900)]
CAPACITY_WH = VOLTAGE * sum(ah for _, _, ah in BATTERIES)  # 51,2 kWh
# Laderegler (MPPT) am DC-Bus: Instanz, Name, Wp, Verschiebung der Spitze in Stunden (Ausrichtung)
MPPTS = [(278, "MPPT Südost", 435, -1.6), (279, "MPPT Süd", 300, 0.0), (280, "MPPT Gartenhaus", 260, 0.9)]
SOC_MIN, SOC_MAX = 16.0, 75.0  # Ladegrenzen des Akkus in %
START = time.time()
state = {"soc": 50.0, "t": None, "battery": 0.0, "mppt": {}}
# Pfad in com.victronenergy.system -> (Register, Faktor) laut Liste 3.81
REGISTERS = {
    "/Ac/PvOnOutput/L1/Power": (808, 1), "/Ac/PvOnOutput/L2/Power": (809, 1), "/Ac/PvOnOutput/L3/Power": (810, 1),
    "/Ac/PvOnGrid/L1/Power": (811, 1), "/Ac/PvOnGrid/L2/Power": (812, 1), "/Ac/PvOnGrid/L3/Power": (813, 1),
    "/Ac/PvOnGenset/L1/Power": (814, 1), "/Ac/PvOnGenset/L2/Power": (815, 1), "/Ac/PvOnGenset/L3/Power": (816, 1),
    "/Ac/Consumption/L1/Power": (817, 1), "/Ac/Consumption/L2/Power": (818, 1), "/Ac/Consumption/L3/Power": (819, 1),
    "/Ac/Grid/L1/Power": (820, 1), "/Ac/Grid/L2/Power": (821, 1), "/Ac/Grid/L3/Power": (822, 1),
    "/Ac/Genset/L1/Power": (823, 1), "/Ac/Genset/L2/Power": (824, 1), "/Ac/Genset/L3/Power": (825, 1),
    "/Ac/ActiveIn/Source": (826, 1),
    "/Dc/Battery/Voltage": (840, 10), "/Dc/Battery/Current": (841, 10), "/Dc/Battery/Power": (842, 1),
    "/Dc/Battery/Soc": (843, 1), "/Dc/Battery/State": (844, 1),
    "/Dc/Pv/Power": (850, 1), "/Dc/Pv/Current": (851, 10),
}


def sim_time():
    """Simulierte Ortszeit; mit SPEED > 1 läuft sie ab dem Start schneller."""
    return time.localtime(START + (time.time() - START) * SPEED)


def weather(day):
    """Wetter je Tag, für denselben Tag immer gleich: Wolkenanteil 0 bis 1 und wie stark er schwankt."""
    kind = WEATHER if WEATHER != "auto" else random.Random(day).choice(["sonnig", "sonnig", "wechselhaft", "bedeckt"])
    return {"sonnig": (0.05, 0.05), "wechselhaft": (0.4, 0.5), "bedeckt": (0.8, 0.1)}[kind]


def sun(t, shift=0.0):
    """Ertrag 0 bis 1 nach Uhrzeit und Jahreszeit (Mitteleuropa, grob), shift verschiebt die Spitze für die
    Ausrichtung in Stunden; Wolken als Summe von Sinuswellen."""
    hour, doy = t.tm_hour + t.tm_min / 60 + t.tm_sec / 3600, t.tm_yday
    season = math.cos((doy - 172) / 365 * 2 * math.pi)  # 1 im Juni, -1 im Dezember
    half = 6 + 2.2 * season  # halbe Tageslänge in Stunden
    height = max(0.0, math.cos((hour - 13.2 - shift) / half * math.pi / 2)) * (0.7 + 0.3 * season)
    cover, swing = weather(t.tm_year * 1000 + doy)
    r = random.Random(t.tm_year * 1000 + doy)
    clouds = cover + swing * sum(math.sin(hour * r.uniform(1, 9) + r.uniform(0, 6)) for _ in range(3)) / 3
    return height * (1 - 0.85 * max(0.0, min(1.0, clouds)))


def house(t):
    """Hausverbrauch je Phase: Grundlast, Kühlschrank, Frühstück, Mittag, Abendessen, Fernsehen, Zufallsgeräte."""
    minute = t.tm_hour * 60 + t.tm_min
    l1 = 120 + (90 if minute % 45 < 15 else 0)  # Kühlschrank
    if 6 * 60 + 40 <= minute < 6 * 60 + 44 or 7 * 60 + 10 <= minute < 7 * 60 + 13:
        l1 += 2000  # Wasserkocher
    if 12 * 60 <= minute < 12 * 60 + 25 or 18 * 60 + 15 <= minute < 18 * 60 + 50:
        l1 += 1400  # Herd
    if 19 * 60 <= minute < 23 * 60:
        l1 += 110  # Fernsehen
    wash = random.Random(t.tm_yday).randrange(9 * 60, 16 * 60)  # jeden Tag zu anderer Zeit
    l2 = 50 + (1900 if wash <= minute < wash + 70 and minute % 10 < 6 else 0)  # Waschmaschine heizt in Stößen
    return [round(l1 + random.uniform(-15, 15)), round(l2 + random.uniform(-5, 5)), round(35 + random.uniform(-3, 3))]


def values():
    """Aktuelle Werte zur simulierten Zeit."""
    now = time.time()
    hours = 0 if state["t"] is None else (now - state["t"]) * SPEED / 3600
    state["t"] = now
    return step(sim_time(), hours)


def step(t, hours):
    """Ein Schritt zur Zeit t (struct_time), hours seit dem letzten: Akku regelt mit Verzögerung auf
    Nulleinspeisung, Rest über das Netz."""
    state["mppt"] = {inst: round(wp * 0.92 * sun(t, shift) * random.uniform(0.98, 1.02)) for inst, _, wp, shift in MPPTS}
    pv_dc = sum(state["mppt"].values())
    pv_ac = round(min(800, PV_AC_WP * 0.92 * sun(t, 1.5) * random.uniform(0.98, 1.02)))  # Südwest, auf 800 W begrenzt  # Wechselrichter auf 800 W begrenzt
    load = house(t)
    target = max(-BATTERY_W, min(BATTERY_W, pv_dc + pv_ac - sum(load)))  # + Laden
    if (target > 0 and state["soc"] >= SOC_MAX) or (target < 0 and state["soc"] <= SOC_MIN):
        target = 0
    state["battery"] += 0.6 * (target - state["battery"])  # regelt nach, Spitzen gehen kurz ins Netz
    battery = round(state["battery"])
    state["soc"] = max(SOC_MIN, min(SOC_MAX, state["soc"] + battery * hours / CAPACITY_WH * 100))
    v = VOLTAGE + state["soc"] / 50
    return {p: 0 for p in REGISTERS} | {
        "/Ac/PvOnGrid/L1/Power": pv_ac, "/Dc/Pv/Power": pv_dc, "/Dc/Pv/Current": round(pv_dc / v, 1),
        "/Ac/Consumption/L1/Power": load[0], "/Ac/Consumption/L2/Power": load[1], "/Ac/Consumption/L3/Power": load[2],
        "/Ac/Grid/L1/Power": load[0] - pv_ac - pv_dc + battery, "/Ac/Grid/L2/Power": load[1],  # + Bezug
        "/Ac/Grid/L3/Power": load[2], "/Ac/ActiveIn/Source": 1,
        "/Dc/Battery/Voltage": round(v, 2), "/Dc/Battery/Current": round(battery / v, 1),
        "/Dc/Battery/Power": battery, "/Dc/Battery/Soc": round(state["soc"]),
        "/Dc/Battery/State": 1 if battery > 0 else 2 if battery < 0 else 0}


# --- MQTT ---------------------------------------------------------------------------------------------------------
keepalive = {"until": 0.0}


def chargers():
    """Topics der Laderegler (com.victronenergy.solarcharger) und Akkus (com.victronenergy.battery). Parallele Akkus
    teilen sich Spannung und Ladestand, die Leistung nach Kapazität."""
    out = {}
    for inst, name, _, _ in MPPTS:
        out |= {f"solarcharger/{inst}/Yield/Power": state["mppt"].get(inst, 0), f"solarcharger/{inst}/CustomName": name,
                f"solarcharger/{inst}/ProductName": "SmartSolar MPPT 100/20"}
    total_ah, v = sum(ah for _, _, ah in BATTERIES), VOLTAGE + state["soc"] / 50
    for inst, name, ah in BATTERIES:
        power = round(state["battery"] * ah / total_ah)
        out |= {f"battery/{inst}/Dc/0/Power": power, f"battery/{inst}/Dc/0/Voltage": round(v, 2),
                f"battery/{inst}/Dc/0/Current": round(power / v, 1), f"battery/{inst}/Soc": round(state["soc"], 1),
                f"battery/{inst}/CustomName": name, f"battery/{inst}/ProductName": "SmartShunt 500A/50mV"}
    return out


def publish_all(client, echo=None):
    for path, value in values().items():
        client.publish(f"N/{PORTAL_ID}/system/0{path}", json.dumps({"value": value}))
    for topic, value in chargers().items():
        client.publish(f"N/{PORTAL_ID}/{topic}", json.dumps({"value": value}))
    client.publish(f"N/{PORTAL_ID}/system/0/Serial", json.dumps({"value": PORTAL_ID}))
    client.publish(f"N/{PORTAL_ID}/full_publish_completed",
                   json.dumps({"value": int(time.time()), **({"full-publish-completed-echo": echo} if echo else {})}))


def on_message(client, _userdata, msg):
    rest = msg.topic.split("/", 2)[-1]  # auch R/<Portal-ID> ohne Pfad
    if rest in ("keepalive", "system/0/Serial"):  # system/0/Serial: alte Form des Keepalive
        try:  # fremde Nutzlast darf die MQTT-Schleife nicht beenden
            opts = list(json.loads(msg.payload).get("keepalive-options", [])) if msg.payload else []
        except (ValueError, AttributeError, TypeError):
            opts = []
        keepalive["until"] = time.time() + 60
        if "suppress-republish" not in opts:
            publish_all(client, next((o.get("full-publish-completed-echo") for o in opts if isinstance(o, dict)), None))


def run_mqtt():
    import paho.mqtt.client as mqtt  # erst hier: der Verlauf läuft im Balkonaut-Image ohne paho
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = lambda c, *_: c.subscribe(f"R/{PORTAL_ID}/#")
    client.on_message = on_message
    client.connect(os.environ.get("MQTT_HOST", "mosquitto"), int(os.environ.get("MQTT_PORT", 1883)))
    client.loop_start()
    last, tick = {}, 0
    while True:
        time.sleep(1)
        tick += 1
        if tick % 5 == 0:
            client.publish(f"N/{PORTAL_ID}/system/0/Serial", json.dumps({"value": PORTAL_ID}))
        if time.time() < keepalive["until"]:  # nur Änderungen, wie der GX
            now = {f"system/0{p}": v for p, v in values().items()} | chargers()
            for topic, value in now.items():
                if last.get(topic) != value:
                    client.publish(f"N/{PORTAL_ID}/{topic}", json.dumps({"value": value}))
            last = now


# --- Modbus TCP -----------------------------------------------------------------------------------------------------
def registers():
    regs = {800 + i: int.from_bytes(PORTAL_ID.encode()[2 * i:2 * i + 2].ljust(2, b"\0")) for i in range(6)}  # Serial
    for path, value in values().items():
        address, factor = REGISTERS[path]
        regs[address] = round(value * factor) & 0xFFFF  # int16 als Zweierkomplement
    return regs


async def modbus(reader, writer):
    try:
        while True:
            tid, _, length, unit = struct.unpack(">HHHB", await reader.readexactly(7))
            if not 2 <= length <= 254:  # Modbus TCP: Unit-ID plus höchstens 253 Bytes
                break
            pdu = await reader.readexactly(length - 1)
            fc, regs = pdu[0], registers()
            start, count = struct.unpack(">HH", pdu[1:5]) if len(pdu) >= 5 else (0, 0)
            if unit not in (0, 100):
                body = bytes([fc | 0x80, 0x0B])
            elif fc not in (3, 4):
                body = bytes([fc | 0x80, 0x01])
            elif not 1 <= count <= 125:
                body = bytes([fc | 0x80, 0x03])
            elif any(a not in regs for a in range(start, start + count)):
                body = bytes([fc | 0x80, 0x02])
            else:
                body = bytes([fc, 2 * count]) + b"".join(struct.pack(">H", regs[a]) for a in range(start, start + count))
            writer.write(struct.pack(">HHHB", tid, 0, len(body) + 1, unit) + body)
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    writer.close()


async def main():
    threading.Thread(target=run_mqtt, daemon=True).start()
    server = await asyncio.start_server(modbus, "0.0.0.0", int(os.environ.get("MODBUS_PORT", 502)))
    print(f"Victron-GX-Mock: Portal-ID {PORTAL_ID}, Modbus TCP Port {server.sockets[0].getsockname()[1]}", flush=True)
    await server.serve_forever()


# --- Verlauf --------------------------------------------------------------------------------------------------------
TEST_CONFIG = {  # für eine neue Test-Instanz im selben Compose-Projekt
    "devices": [{"type": "victron_modbus", "host": "gx"}],  # über MQTT: type victron_mqtt, host mosquitto
    "location": {"lat": 50.0, "lon": 10.0},
    "planes": [{"declination": 30, "azimuth": 150, "kwp": 0.87, "inverter": "storage"},
               {"declination": 30, "azimuth": 250, "kwp": 0.87, "inverter": "extra"}],
    "prices": {"energy": 0.32, "feed_in": 0.0},
    "system": {"cost": 1200.0},
}


def history():
    """Die letzten DAYS Tage alle 10 s wie der Collector in die leere Datenbank, Stunde für Stunde aggregiert und mit
    Regelgüte je Tag, wie bei einer Anlage, die so lange läuft. Geht über dieselbe Zuordnung wie der Adapter."""
    from app import config
    from balkonaut import devices, views
    from balkonaut.storage import Storage
    data = config.data_dir()
    if not (data / "config.yaml").exists():
        config.save(data / "config.yaml", TEST_CONFIG | {"system": {**TEST_CONFIG["system"],
                    "commissioned": time.strftime("%Y-%m-%d", time.localtime(time.time() - DAYS * 86400))}})
    storage = Storage(data / "balkonaut.db")
    if storage.first() is not None:
        print("Datenbank hat schon Messwerte, Verlauf bleibt unverändert (für einen neuen balkonaut.db löschen).")
        return  # kein Fehler: der Stack startet den Verlauf bei jedem Hochfahren
    storage.db.executescript("PRAGMA synchronous = OFF; PRAGMA journal_mode = MEMORY")  # schneller; bei Absturz neu erzeugen
    prices = config.load(data / "config.yaml")["prices"]
    end = int(time.time()) // 10 * 10
    for ts in range((end - DAYS * 86400) // 3600 * 3600, end, 10):
        storage.add(ts, devices._victron(step(time.localtime(ts), 10 / 3600)))
        if ts % 3600 == 0:
            storage.aggregate(ts)
            if ts % 86400 == 0:
                views.store_regulation_days(storage, prices, ts)
                print(time.strftime("%d.%m.%Y", time.localtime(ts)), f"Ladestand {state['soc']:.0f} %", flush=True)
    storage.aggregate(end)
    views.store_regulation_days(storage, prices, end)
    print(f"{DAYS} Tage Verlauf in {data / 'balkonaut.db'}")


if __name__ == "__main__":
    history() if sys.argv[1:] == ["history"] else asyncio.run(main())
