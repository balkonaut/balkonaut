import asyncio
import importlib.metadata
import json
import logging
import math
import socket
import time
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from balkonaut import analytics, collector, devices, pvgis, views
from balkonaut.profiles import direction
from balkonaut.storage import Storage

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def de(value, digits=1):
    """Zahl im deutschen Format, fehlende Werte als Strich."""
    if not isinstance(value, (int, float)):
        return "–"
    value = round(value, digits) + 0.0  # -0.0 und gerundete Winzlinge wie -0.01 ohne Minus
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


templates.env.filters.update(
    de=de,
    abs_de=lambda v, d=1: de(abs(v) if isinstance(v, (int, float)) else None, d),
    pct=lambda v: "–" if v is None else de(v * 100, 0) + " %",
    komma=lambda v: v if isinstance(v, str) else f"{v:g}".replace(".", ","),  # Eingabefelder: 50,1 statt 50.1
    ago=lambda s: f"{s} s" if s < 120 else f"{s // 60} min" if s < 7200 else f"{s // 3600} h",
)
templates.env.globals["version"] = importlib.metadata.version("balkonaut")
templates.env.globals.update(kacheln=views.KACHELN, guete=views.guete)
# Adresse, unter der die Integration das Add-on erreicht (Hostname des Add-on-Containers im HA-Netz)
templates.env.globals["integration_url"] = lambda: f"http://{socket.gethostname()}:8000" if config.addon() else None
PERIODS = [("tag", "Heute"), ("monat", "Monat"), ("jahr", "Jahr"), ("gesamt", "Gesamt")]
SUPERVISOR_IP = "172.30.32.2"  # Absender von Ingress-Anfragen im Add-on


def chart(bars):
    """Balken, Maßstab (Höhe 140 Einheiten), Beschriftung der y-Achse in kWh und Prognose als Punkte der Linie
    (Mitte jedes Zeitabschnitts) für das SVG-Diagramm."""
    peak = max((max(b["own"], b["grid"], b["gen"], b.get("fc") or 0) for b in bars), default=0)
    ticks = []
    if peak:
        raw = peak / 8  # etwa acht Hilfslinien mit runden Werten (1, 2, 5 × 10^n)
        mag = 10 ** math.floor(math.log10(raw))
        step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
        digits = max(0, -math.floor(math.log10(step)))
        ticks = [(i * step, de(i * step, digits)) for i in range(1, int(peak / step + 1e-9) + 1)]
    scale, w = (140 / peak if peak else 0), (480 - 36) / max(len(bars), 1)
    forecast = " ".join(f"{36 + (i + 0.5) * w:.1f},{150 - (b.get('fc') or 0) * scale:.1f}" for i, b in enumerate(bars))
    return {"bars": bars, "scale": scale, "ticks": ticks,
            "forecast": forecast if any(b.get("fc") for b in bars) else None}


def soc_gauge(live):
    """Akku-Ring: Ladestand, Farbton von 0 (rot, Untergrenze) bis 130 (grün, Obergrenze) und Grenzmarken
    als Striche im Ring (viewBox 100, Radius 34 bis 50). None ohne Ladestand."""
    soc = live.get("battery_soc")
    if soc is None:
        return None
    lo, hi = live.get("battery_soc_min") or 0, live.get("battery_soc_max") or 100
    marks = []
    for key, name, value in (("lo", "Minimum", live.get("battery_soc_min")),
                             ("prot", "Entladeschutz", live.get("battery_discharge_protection")),
                             ("hi", "Maximum", live.get("battery_soc_max"))):
        if value is not None:
            c, s = math.cos(value / 100 * 2 * math.pi), math.sin(value / 100 * 2 * math.pi)
            marks.append({"key": key, "name": name, "value": value,
                          "x1": round(50 + 34 * c, 2), "y1": round(50 + 34 * s, 2),
                          "x2": round(50 + 50 * c, 2), "y2": round(50 + 50 * s, 2)})
    share = (soc - lo) / (hi - lo) if hi > lo else 1
    # Restzeit bis zur Obergrenze (laden) bzw. Minimum oder Entladeschutz (entladen)
    # ponytail: ohne Wandlungsverluste und bei gleichbleibender Leistung, Verlauf glätten falls es springt
    power, cap, rest = live.get("battery_power") or 0, live.get("battery_capacity"), None
    target = hi if power > 0 else max(lo, live.get("battery_discharge_protection") or 0)
    if cap and abs(power) >= 20 and (target - soc) * power > 0:
        minutes = round((target - soc) / 100 * cap * 60000 / power)
        rest = {"target": target, "minutes": minutes} if minutes <= 48 * 60 else None
    return {"soc": soc, "lo": lo, "hi": hi, "hue": round(min(max(share, 0), 1) * 130), "marks": marks, "rest": rest}


log = logging.getLogger(__name__)


async def load_profile(app, adapter, cache):
    """Ertragsprofil (kWh je Monat) aus Forecast.Solar-Flächen und PVGIS, zwischengespeichert in cache."""
    old = json.loads(cache.read_text()) if cache.exists() else None
    try:
        lat, lon, planes = await asyncio.to_thread(adapter.solar_planes)
        key = {"lat": round(lat, 2), "lon": round(lon, 2), "planes": [list(p) for p in planes]}  # ~1 km genau
        if not planes or (old and old["key"] == key):
            app.state.profile = old["profile"] if old and planes else None
            return
        profile = await asyncio.to_thread(pvgis.monthly, key["lat"], key["lon"], planes)
        cache.write_text(json.dumps({"key": key, "profile": profile}))
        app.state.profile = profile
    except Exception as e:  # HA oder PVGIS nicht erreichbar: letztes bekanntes Profil nutzen
        log.warning("Ertragsprofil nicht aktualisiert: %s", e)
        app.state.profile = old["profile"] if old else None


@asynccontextmanager
async def lifespan(app):
    data = config.data_dir()
    data.mkdir(parents=True, exist_ok=True)
    app.state.config_path = data / "config.yaml"
    cfg = config.load(app.state.config_path)
    app.state.storage = Storage(data / "balkonaut.db")
    app.state.profile = None
    app.state.tasks = []
    start_measuring(app, cfg)
    yield
    for task in app.state.tasks:
        task.cancel()


def start_measuring(app, cfg):
    """Messung, Ertragsprofil und Regelgüte mit dem Adapter aus der Konfiguration (neu) starten."""
    for task in app.state.tasks:
        task.cancel()
    app.state.tasks = []
    adapter = config.adapter(cfg)
    app.state.forecast = adapter.forecast if adapter else None  # Prognose je Stunde für das Diagramm
    if adapter:
        app.state.tasks = [asyncio.create_task(collector.run(adapter, app.state.storage)),
                           asyncio.create_task(load_profile(app, adapter, app.state.config_path.parent / "ertragsprofil.json")),
                           asyncio.create_task(regulation_job(app))]


app = FastAPI(title="Balkonaut", lifespan=lifespan)


@app.middleware("http")
async def addon_writes_via_ingress(request: Request, call_next):
    """Im Add-on ändern nur Anfragen über Ingress (vom Supervisor) die Einstellungen; lesen dürfen auch
    andere Container im HA-Netz, z. B. die Integration."""
    sender = request.client and request.client.host
    if config.addon() and request.method not in ("GET", "HEAD") and sender != SUPERVISOR_IP:
        return PlainTextResponse("Einstellungen nur über Home Assistant änderbar", status_code=403)
    return await call_next(request)
# Gebautes Handbuch (MkDocs), im Container unter /srv/handbuch
app.mount("/handbuch", StaticFiles(directory=Path(__file__).parent.parent / "handbuch", html=True, check_dir=False))


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/status")
def api_status(request: Request):
    """Aktuelle Messwerte, Bilanz und Akku für heute, Monat, Jahr und gesamt sowie Amortisation.
    Felder: siehe Handbuch, Schnittstelle."""
    cfg = config.load(request.app.state.config_path)
    storage = request.app.state.storage
    now = time.time()
    return analytics.status(storage.hourly(int(now)), storage.latest(), now, cfg["prices"], cfg["system"]["cost"],
                            config.commissioned(cfg), request.app.state.profile)


@app.get("/api/v1/export")
def api_export(request: Request):
    """Gesamte Historie (Stundenwerte, Tageswerte der Regelgüte) für den Umzug in die Home-Assistant-Integration."""
    return request.app.state.storage.export()


@app.get("/api/v1/verlauf")
def api_history(request: Request, ansicht: str = "tag", datum: str = ""):
    """Balken einer Verlaufsansicht (tag, woche, monat, jahr) und Bilanz des Zeitraums."""
    return history_data(request, ansicht, datum)


def report_data(request, monat):
    cfg = config.load(request.app.state.config_path)
    return views.report(request.app.state.storage, monat, cfg["prices"], time.time(), config.commissioned(cfg))


@app.get("/api/v1/bericht")
def api_report(request: Request, monat: str = ""):
    """Monatsbericht (monat=JJJJ-MM, Standard: aktueller Monat)."""
    return report_data(request, monat)


@app.get("/bericht", include_in_schema=False)
def report(request: Request, monat: str = ""):
    r = report_data(request, monat)
    return templates.TemplateResponse(request, "report.html", {"r": r, "chart": chart(r["tage"])})


@app.get("/api/v1/nulleinspeisung")
def api_regulation(request: Request):
    """Regelgüte der Nulleinspeisung der letzten 7 Tage, null ohne Messwerte."""
    return regulation_data(request)


@app.get("/", include_in_schema=False)
def dashboard(request: Request, zeitraum: str = "tag"):
    cfg = config.load(request.app.state.config_path)
    st = api_status(request)
    period = zeitraum if zeitraum in st["bilanz"] else "tag"
    live = st["live"]
    live["pv"] = (live.get("pv_power") or 0) + (live.get("pv_ac_power") or 0) if live else None
    today = datetime.now(analytics.TZ).date()
    bars = analytics.history(request.app.state.storage.hourly(int(time.time())),
                             analytics.buckets("tag", today)[1], cfg["prices"], hourly_forecast(request.app))
    a = st["amortisation"]
    entities = (cfg.get("home_assistant") or {}).get("entities") or {}
    # Einrichtung: (Schritt, Hinweis, erledigt, Link); im Add-on kommen Geräte und Prognose aus dessen Konfiguration
    in_ha = "In Home Assistant: Add-on Balkonaut, Reiter Konfiguration" if config.addon() else None
    setup = [("Geräte eintragen", in_ha or "Per IP-Adresse im Heimnetz, ohne Anmeldung",
              bool(cfg.get("devices") or entities), None if in_ha else "einstellungen#geraete"),
             ("Standort und Flächen", "Flächen eintragen oder im Reiter Konfiguration des Add-ons eine "
              "Prognose-Entität zuordnen" if in_ha else "Für Tagesprognose und Jahresverlauf",
              bool((cfg.get("location") or in_ha) and cfg.get("planes")) or "pv_forecast_today" in entities,
              "einstellungen#flaechen"),
             ("Preise und Anlage", "Ohne Preise stehen Euro-Beträge auf 0",
              cfg["prices"]["energy"] > 0 and cfg["system"]["cost"] > 0, "einstellungen#preise")]
    return templates.TemplateResponse(request, "dashboard.html", {
        "setup": setup,
        "periods": PERIODS, "period": period, "b": st["bilanz"][period], "akku": st["akku"][period],
        "heute": st["bilanz"]["tag"], "live": live, "gauge": soc_gauge(live),
        "live_age": int(time.time() - st["stand"].timestamp()) if st["stand"] else None,
        "chart": chart(bars), "a": a, "warnings": st["warnungen"],
        "progress": min(a["bisher_gespart"] / a["kosten"] * 100, 100) if a["kosten"] else 0,
        "hub_name": next((HUB_NAMES[d["type"]] for d in cfg.get("devices") or [] if d["type"] in HUB_NAMES), "Wechselrichter"),
        "battery_name": (cfg["system"].get("battery_name") or "Akku")[:10],
        "extra_name": (cfg["system"].get("extra_name") or "Zusatz-WR")[:14],
        "modules": {inv: " + ".join(direction(p["azimuth"]).split()[0] for p in cfg.get("planes") or []
                                     if p.get("inverter", "storage") == inv) for inv in ("storage", "extra")},
    })


def history_data(request, ansicht, datum):
    cfg = config.load(request.app.state.config_path)
    return views.history(request.app.state.storage, ansicht, datum, cfg["prices"], time.time(),
                         hourly_forecast(request.app))


def hourly_forecast(app):
    """Erwartete Erzeugung je Stunde heute aus den eingetragenen Flächen, ohne Flächen leer."""
    planes = app.state.forecast
    return planes.current_hours() if planes else {}


@app.get("/verlauf", include_in_schema=False)
def history(request: Request, ansicht: str = "tag", datum: str = ""):
    d = history_data(request, ansicht, datum)
    return templates.TemplateResponse(request, "history.html", {
        "views": views.VIEWS.items(), "view": d["ansicht"], "title": d["titel"], "prev": d["zurueck"], "next": d["weiter"],
        "chart": chart(d["balken"]), "b": d["bilanz"],
    })


async def regulation_job(app):
    while True:  # stündlich; neue Tage kommen nach Mitternacht dazu
        try:
            await asyncio.to_thread(views.store_regulation_days, app.state.storage,
                                    config.load(app.state.config_path)["prices"], time.time())
        except Exception:
            log.exception("Tageswerte der Regelgüte nicht gespeichert")
        await asyncio.sleep(3600)


def regulation_data(request):
    cfg = config.load(request.app.state.config_path)
    return views.regulation_week(request.app.state.storage, cfg["prices"], time.time())


@app.get("/nulleinspeisung", include_in_schema=False)
def zero_feed_in(request: Request):
    return templates.TemplateResponse(request, "regulation.html", {"r": regulation_data(request)})


DEVICE_NAMES = {"apsystems_ezhi": "APsystems EZHI", "shelly_em": "Shelly 3EM", "shelly_em1": "Shelly EM (eine Phase)",
                "shelly_plug": "Shelly Plug", "opendtu": "Hoymiles über OpenDTU", "ahoydtu": "Hoymiles über AhoyDTU"}
HUB_NAMES = {"apsystems_ezhi": "EZHI", "opendtu": "Hoymiles", "ahoydtu": "Hoymiles"}  # Mitte des Energieflusses
INVERTIBLE = {"shelly_plug": "output_power", "shelly_em": "grid_power", "shelly_em1": "grid_power"}  # Richtung je nach Anschluss
# Anzeige der aktuellen Werte: Messgröße, Name, Einheit, Richtung bei + und -
LIVE = [("grid_power", "Netz", "W", ("Bezug", "Einspeisung")), ("pv_power", "PV", "W", None),
        ("pv_ac_power", "Off-Grid-Port", "W", None), ("battery_power", "Akku", "W", ("lädt", "entlädt")),
        ("battery_soc", "Ladestand", "%", None), ("output_power", "Abgabe", "W", ("", "Bezug, Vorzeichen prüfen")),
        ("output_energy", "Zähler", "kWh", None)]


def device_values(dev):
    """Aktuelle Werte eines Geräts als Text mit Richtung, z. B. „Netz 312 W (Bezug)“; None, wenn es nicht antwortet."""
    if not (values := devices.Devices([dev]).read()):  # leer: Gerät antwortet nicht
        return None
    out = []
    for key, label, unit, words in LIVE:
        if (value := values.get(key)) is not None:
            text = f"{label} {de(abs(value) if words else value, 1 if unit == 'kWh' else 0)} {unit}"
            if words and round(value) and (word := words[value < 0]):
                text += f" ({word})"
            out.append(text)
    return out


async def settings_page(request, cfg, status_code=200, **errors):
    live = await asyncio.to_thread(lambda: [device_values(d) for d in cfg.get("devices") or []])
    return templates.TemplateResponse(request, "settings.html", {
        "cfg": cfg, "live": live, "names": DEVICE_NAMES, "invertible": INVERTIBLE, "addon": config.addon(), **errors},
        status_code=status_code)


@app.get("/einstellungen", include_in_schema=False)
async def settings(request: Request):
    return await settings_page(request, config.load(request.app.state.config_path))


async def form_data(request):
    return {k: v for k, v in parse_qs((await request.body()).decode(), keep_blank_values=True).items()}


def save_and_restart(request, cfg, anchor):
    config.save(request.app.state.config_path, cfg)
    start_measuring(request.app, cfg)
    return RedirectResponse(f"einstellungen?gespeichert=1#{anchor}", status_code=303)  # relativ wegen Ingress


async def save_devices(request, cfg, form):
    """Gerät hinzufügen (Typ wird erkannt), entfernen oder seine Richtung drehen."""
    form = {k: v[0].strip() for k, v in form.items()}
    devs, host = cfg.setdefault("devices", []), form.get("host", "")
    if form.get("aktion") == "hinzufuegen":
        if not host:
            return await settings_page(request, cfg, 400, device_error="Bitte die IP-Adresse des Geräts eingeben.")
        if any(d["host"] == host for d in devs):
            return await settings_page(request, cfg, 400, device_error=f"{host} ist schon eingetragen.")
        try:
            devs.append({"type": await asyncio.to_thread(devices.detect, host), "host": host})
        except ValueError:
            return await settings_page(request, cfg, 400, device_error=(
                f"Unter {host} antwortet kein bekanntes Gerät. Adresse prüfen; unterstützt sind APsystems EZHI "
                "(lokaler Modus in der APsystems-App), Shelly-Zähler, Shelly Plug und Hoymiles über OpenDTU oder "
                "AhoyDTU (IP-Adresse der DTU)."))
    elif form.get("aktion") == "entfernen":
        cfg["devices"] = [d for d in devs if d["host"] != host]
    elif form.get("aktion") == "drehen":
        for d in devs:
            if d["host"] == host and d["type"] in INVERTIBLE:
                d["invert"] = [] if d.get("invert") else [INVERTIBLE[d["type"]]]
    if not cfg["devices"]:
        del cfg["devices"]
    return save_and_restart(request, cfg, "geraete")


async def save_planes(request, cfg, form):
    """Standort und Flächen; leere Zeilen fallen weg, so lässt sich eine Fläche auch entfernen. Bei Fehlern bleiben
    die Eingaben stehen und die Meldung nennt das Feld."""
    def num(text, low, high, what):
        try:
            value = float(text.replace("°", "").replace(",", ".").strip())
        except ValueError:
            raise ValueError(f"{what}: bitte eine Zahl eingeben") from None
        if not low <= value <= high:
            raise ValueError(f"{what}: {de(low, 0)} bis {de(high, 0)}")
        return value
    lat, lon = (form.get(k, [""])[0].strip() for k in ("lat", "lon"))
    rows = [{"declination": d, "azimuth": a, "kwp": k, "inverter": i} for d, a, k, i in zip(
        form.get("declination", []), form.get("azimuth", []), form.get("kwp", []), form.get("inverter", []))
        if d.strip() or a.strip() or k.strip()]
    errors, location, planes = [], None, []
    if lat or lon:
        try:
            location = {"lat": num(lat, -90, 90, "Breitengrad"), "lon": num(lon, -180, 180, "Längengrad")}
        except ValueError as e:
            errors.append(str(e))
    for n, row in enumerate(rows, 1):
        try:
            planes.append({"declination": num(row["declination"], 0, 90, f"Fläche {n}, Neigung"),
                           "azimuth": num(row["azimuth"], 0, 360, f"Fläche {n}, Ausrichtung"),
                           "kwp": num(row["kwp"], 0.01, 100, f"Fläche {n}, Leistung"),
                           "inverter": "extra" if row["inverter"] == "extra" else "storage"})
        except ValueError as e:
            errors.append(str(e))
    if rows and not (lat or lon) and not config.addon():  # im Add-on gilt dann der Standort von Home Assistant
        errors.append("Für die Flächen fehlt der Standort: Breiten- und Längengrad eintragen")
    if errors:
        return await settings_page(request, cfg, 400, planes_error=errors,
                                   entered={"location": {"lat": lat, "lon": lon}, "planes": rows})
    for key, value in (("location", location), ("planes", planes)):
        if value:
            cfg[key] = value
        else:
            cfg.pop(key, None)
    return save_and_restart(request, cfg, "flaechen")


@app.post("/einstellungen", include_in_schema=False)
async def save_settings(request: Request):
    multi = await form_data(request)
    cfg = config.load(request.app.state.config_path)
    bereich = (multi.get("bereich") or [""])[0]
    if bereich in ("geraete", "flaechen"):
        if bereich == "geraete" and config.addon():  # das Add-on liest die Geräte über Home Assistant
            return PlainTextResponse("Im Add-on nicht verfügbar", status_code=404)
        return await (save_devices if bereich == "geraete" else save_planes)(request, cfg, multi)
    form = {k: v[0] for k, v in multi.items()}
    try:
        values = {k: float(form[k].replace(",", ".")) for k in ("energy", "feed_in", "cost")}
        day = date.fromisoformat(form["commissioned"]) if form.get("commissioned") else None
        if min(values.values()) < 0 or (day and day > date.today()):
            raise ValueError
    except (KeyError, ValueError):
        return await settings_page(request, cfg, 400, error=True)
    cfg["prices"].update(energy=values["energy"], feed_in=values["feed_in"])
    cfg["system"].update(cost=values["cost"], commissioned=day, battery_name=form.get("battery_name", "").strip() or None,
                         extra_name=form.get("extra_name", "").strip() or None)
    config.save(request.app.state.config_path, cfg)
    return RedirectResponse("einstellungen?gespeichert=1", status_code=303)  # relativ wegen Ingress
