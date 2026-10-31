"""Mock einer Hoymiles-DTU mit einem HM-800 und einem HMS-800W-2T, für Tests ohne Gerät.

Hoymiles HM und HMS haben keine eigene lokale Schnittstelle, im Heimnetz liest man sie über OpenDTU oder AhoyDTU.
DTU legt fest, welche nachgebildet wird, nach deren Quellcode:
- opendtu (src/WebApi_ws_live.cpp): GET /api/livedata/status mit inverters, total (Power W, YieldDay Wh,
  YieldTotal kWh, je {"v", "u", "d"}) und hints. Vereinfachung: ?inv=<Seriennummer> liefert nur die Übersicht ohne
  AC/DC/INV-Kanäle, Balkonaut liest nur total.
- ahoydtu (src/web/RestApi.h): GET /api/generic (u. a. esp_type, modules) und /api/index (inverter mit cur_pwr).
Sonne und Wetter wie gx.py (SPEED, WEATHER), Port 80 im Container.
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import gx

DTU = os.environ.get("DTU", "opendtu")
# Seriennummer, Name, Wp der beiden Module, Verschiebung der Spitze in Stunden (Ausrichtung), Zähler beim Start in kWh
INVERTERS = [("116183000001", "HM-800 Süd", 820, 0.0, 1234.5), ("141283000002", "HMS-800W-2T West", 860, 1.5, 456.7)]
MAX_W = 800
lock = threading.Lock()
state = {"t": time.time(), "day": None, "power": {}, "today": {}, "total": {s: kwh * 1000 for s, *_, kwh in INVERTERS}}


def update():
    """Leistung je Wechselrichter jetzt, Erträge seit der letzten Abfrage aufaddiert (Wh), um Mitternacht YieldDay 0."""
    with lock:
        now, t = time.time(), gx.sim_time()
        hours, state["t"] = (now - state["t"]) * gx.SPEED / 3600, now
        if state["day"] != t.tm_yday:
            state["day"], state["today"] = t.tm_yday, {s: 0.0 for s, *_ in INVERTERS}
        for serial, _, wp, shift, _ in INVERTERS:
            p = min(wp * gx.sun(t, shift) * 0.95, MAX_W)  # 95 % Wirkungsgrad, gedeckelt auf die Nennleistung
            state["power"][serial] = round(p, 1)
            state["today"][serial] += p * hours
            state["total"][serial] += p * hours
        return dict(state["power"]), dict(state["today"]), dict(state["total"])


def opendtu():
    power, today, total = update()
    field = lambda v, u, d: {"v": round(v, d), "u": u, "d": d}
    inverters = [{"serial": s, "name": name, "order": i, "data_age": 0, "data_age_ms": 0, "poll_enabled": True,
                  "reachable": True, "producing": power[s] > 0, "limit_relative": 100.0, "limit_absolute": MAX_W,
                  "radio_stats": {"tx_request": 0, "tx_re_request": 0, "rx_success": 0, "rx_fail_nothing": 0,
                                  "rx_fail_partial": 0, "rx_fail_corrupt": 0, "rssi": -60}}
                 for i, (s, name, *_) in enumerate(INVERTERS)]
    return {"inverters": inverters,
            "total": {"Power": field(sum(power.values()), "W", 1), "YieldDay": field(sum(today.values()), "Wh", 0),
                      "YieldTotal": field(sum(total.values()) / 1000, "kWh", 3)},
            "hints": {"time_sync": False, "radio_problem": False, "default_password": False, "pin_mapping_issue": False}}


def ahoy_generic():
    return {"wifi_rssi": -60, "ts_uptime": int(time.time() - gx.START), "ts_now": int(time.time()), "version": "0.8.155",
            "modules": "", "build": "mock", "env": "esp32-wroom32", "host": "ahoy-dtu", "menu_prot": False,
            "menu_mask": 0, "menu_protEn": False, "cst_lnk": "", "cst_lnk_txt": "", "region": 0, "timezone": 1,
            "esp_type": "ESP32"}


def ahoy_index():
    power, *_ = update()
    now = int(time.time())
    return {"generic": ahoy_generic(), "ts_now": now, "ts_sunrise": 0, "ts_sunset": 0, "ts_offsSr": 0, "ts_offsSs": 0,
            "inverter": [{"enabled": True, "id": i, "name": name, "cur_pwr": power[s], "is_avail": True,
                          "is_producing": power[s] > 0, "ts_last_success": now}
                         for i, (s, name, *_) in enumerate(INVERTERS)],
            "disNightComm": False, "warnings": []}


ROUTES = {"opendtu": {"/api/livedata/status": opendtu},
          "ahoydtu": {"/api/generic": ahoy_generic, "/api/index": ahoy_index}}[DTU]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = ROUTES.get(self.path.split("?")[0])
        if not route:
            self.send_error(404)
            return
        body = json.dumps(route()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keine Zeile je Abfrage
        pass


if __name__ == "__main__":
    print(f"Hoymiles-Mock als {DTU} auf Port 80", flush=True)
    ThreadingHTTPServer(("", 80), Handler).serve_forever()
