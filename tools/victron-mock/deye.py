"""Mock eines Deye-Wechselrichters mit Logger-Stick, für Tests ohne Gerät. DEYE legt fest, welcher:
- micro: SUN800G3 mit zwei Modulen, Statusseite des Sticks GET /status.html mit HTTP-Anmeldung admin/admin und
  Zeilen var webdata_<Feld> = "<Wert>"; (wie turbopixel/deye-inverter-status und wilmsn/simple_deye_crawler lesen).
- hybrid: einphasiger Hybrid (SUN-6K-SG03LP1) mit Akku. UDP 48899 beantwortet die Suche "WIFIKIT-214028-READ" mit
  IP,MAC,Seriennummer; TCP 8899 spricht Solarman V5 (nach pysolarmanv5) mit Modbus RTU, Gerät 1, Funktion 3. Register
  nach deye_hybrid.yaml (ha-solarman): 0 Gerätetyp, 72–75 Akku-Zähler, 96–97 PV-Zähler, 169 Netz (+ Bezug),
  175 Abgabe, 184 Ladestand, 186–187 PV je String, 190 Akku (+ Entladen); unbekannte Register 0.
Sonne, Wetter und Hausverbrauch wie gx.py (SPEED, WEATHER).
"""
import os
import socketserver
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import gx

DEYE = os.environ.get("DEYE", "micro")
SERIAL = 2712345678  # Seriennummer des Logger-Sticks
CAPACITY_WH, BATTERY_W, SOC_MIN, SOC_MAX = 5120, 2500, 10.0, 100.0
lock = threading.Lock()
state = {"t": time.time(), "day": None, "soc": 50.0, "today": 0.0,
         "wh": {"pv": 2_345_600.0, "charge": 812_300.0, "discharge": 734_100.0}}  # Zähler beim Start


def update():
    """Werte zur simulierten Zeit, Zähler seit der letzten Abfrage aufaddiert."""
    with lock:
        now, t = time.time(), gx.sim_time()
        hours, state["t"] = (now - state["t"]) * gx.SPEED / 3600, now
        if state["day"] != t.tm_yday:
            state["day"], state["today"] = t.tm_yday, 0.0
        if DEYE == "micro":
            pv = round(min(800, 860 * 0.95 * gx.sun(t, 0.5)), 1)
            state["today"] += pv * hours
            state["wh"]["pv"] += pv * hours
            return {"pv": pv}
        strings = [round(900 * 0.95 * gx.sun(t, shift)) for shift in (-1.0, 1.0)]  # Südost, Südwest
        load = sum(gx.house(t))
        battery = max(-BATTERY_W, min(BATTERY_W, sum(strings) - load))  # + Laden
        if (battery > 0 and state["soc"] >= SOC_MAX) or (battery < 0 and state["soc"] <= SOC_MIN):
            battery = 0
        state["soc"] = max(SOC_MIN, min(SOC_MAX, state["soc"] + battery * hours / CAPACITY_WH * 100))
        state["wh"]["pv"] += sum(strings) * hours
        state["wh"]["charge" if battery > 0 else "discharge"] += abs(battery) * hours
        return {"strings": strings, "battery": battery, "output": sum(strings) - battery,
                "grid": load - sum(strings) + battery, "soc": round(state["soc"])}


# --- Mikrowechselrichter: Statusseite ------------------------------------------------------------------------------
class StatusPage(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/status.html":
            self.send_error(404)
            return
        if self.headers.get("Authorization") != "Basic YWRtaW46YWRtaW4=":  # admin:admin
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="USER LOGIN"')
            self.end_headers()
            return
        v = update()
        fields = {"sn": SERIAL, "msvn": "MW3_16U_5406_1.53", "ssvn": "", "pv_type": "SUN800G3-EU-230", "rate_p": 800,
                  "now_p": round(v["pv"]), "today_e": round(state["today"] / 1000, 1),
                  "total_e": round(state["wh"]["pv"] / 1000, 1), "alarm": "", "utime": 0}
        body = ("<html><head><script>\n" + "".join(f'var webdata_{k} = "{w}";\n' for k, w in fields.items())
                + "</script></head><body>Deye</body></html>").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


# --- Hybrid: Solarman V5 über den Logger-Stick ---------------------------------------------------------------------
def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = crc >> 1 ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def registers():
    v = update()
    s16 = lambda x: round(x) & 0xFFFF
    regs = {0: 0x0300, 169: s16(v["grid"]), 175: s16(v["output"]), 184: v["soc"], 186: v["strings"][0],
            187: v["strings"][1], 190: s16(-v["battery"])}  # Deye: Akku positiv beim Entladen
    for reg, key in ((72, "charge"), (74, "discharge"), (96, "pv")):
        tenth = round(state["wh"][key] / 100)  # 0,1 kWh, niedriges Wort zuerst
        regs[reg], regs[reg + 1] = tenth & 0xFFFF, tenth >> 16
    return regs


class Logger(socketserver.BaseRequestHandler):
    def read(self, n):
        data = b""
        while len(data) < n:
            if not (chunk := self.request.recv(n - len(data))):
                return b""
            data += chunk
        return data

    def handle(self):
        while (head := self.read(11)) and head[0] == 0xA5:
            length, control, seq, serial = struct.unpack("<HHHI", head[1:])
            rest = self.read(length + 2)
            frame = head + rest
            if control != 0x4510 or serial != SERIAL or frame[-1] != 0x15 or sum(frame[1:-2]) & 0xFF != frame[-2]:
                return  # wie der Stick: falsche Seriennummer oder kaputter Rahmen, keine Antwort
            rtu = rest[15:-2]
            unit, func, start, count = struct.unpack(">BBHH", rtu[:6])
            if func != 3 or crc16(rtu[:6]) != struct.unpack("<H", rtu[6:8])[0]:
                answer = bytes([unit, func | 0x80, 1])
            elif count > 125:
                answer = bytes([unit, 0x83, 3])
            else:
                regs = registers()
                answer = bytes([unit, 3, 2 * count]) + struct.pack(
                    f">{count}H", *(regs.get(r, 0) for r in range(start, start + count)))
            answer += struct.pack("<H", crc16(answer))
            body = struct.pack("<BBIII", 2, 1, 0, 0, 0) + answer  # Rahmentyp, Status, drei Zeiten
            out = struct.pack("<BHHHI", 0xA5, len(body), 0x1510, seq, SERIAL) + body
            self.request.sendall(out + bytes([sum(out[1:]) & 0xFF, 0x15]))


class Search(socketserver.BaseRequestHandler):
    def handle(self):
        data, sock = self.request
        if data.strip() == b"WIFIKIT-214028-READ":
            sock.sendto(f"0.0.0.0,E8FDF8000001,{SERIAL}".encode(), self.client_address)


if __name__ == "__main__":
    print(f"Deye-Mock als {DEYE}", flush=True)
    if DEYE == "micro":
        ThreadingHTTPServer(("", 80), StatusPage).serve_forever()
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    threading.Thread(target=socketserver.UDPServer(("", 48899), Search).serve_forever, daemon=True).start()
    socketserver.ThreadingTCPServer(("", 8899), Logger).serve_forever()
