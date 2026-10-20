import asyncio
import os
from datetime import date
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from balkonaut import analytics, collector
from balkonaut.homeassistant import HomeAssistant
from balkonaut.storage import Storage

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def de(value, digits=1):
    """Zahl im deutschen Format, fehlende Werte als Strich."""
    if not isinstance(value, (int, float)):
        return "–"
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


templates.env.filters.update(
    de=de,
    abs_de=lambda v, d=1: de(abs(v) if isinstance(v, (int, float)) else None, d),
    pct=lambda v: "–" if v is None else de(v * 100, 0) + " %",
    ago=lambda s: f"{s} s" if s < 120 else f"{s // 60} min" if s < 7200 else f"{s // 3600} h",
)
PERIODS = [("tag", "Heute"), ("monat", "Monat"), ("jahr", "Jahr"), ("gesamt", "Gesamt")]


@asynccontextmanager
async def lifespan(app):
    data = Path(os.environ.get("BALKONAUT_DATA", "data"))
    data.mkdir(parents=True, exist_ok=True)
    app.state.config_path = data / "config.yaml"
    cfg = config.load(app.state.config_path)
    app.state.storage = Storage(data / "balkonaut.db")
    task = None
    if ha := cfg.get("home_assistant"):
        adapter = HomeAssistant(ha["url"], ha["token"], {k: tuple(v) for k, v in ha["entities"].items()})
        task = asyncio.create_task(collector.run(adapter, app.state.storage))
    yield
    if task:
        task.cancel()


app = FastAPI(title="Balkonaut", lifespan=lifespan)
# Gebautes Handbuch (MkDocs), im Container unter /srv/handbuch
app.mount("/handbuch", StaticFiles(directory=Path(__file__).parent.parent / "handbuch", html=True, check_dir=False))


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/bilanz")
def bilanz(request: Request):
    cfg = config.load(request.app.state.config_path)
    rows = request.app.state.storage.hourly(int(time.time()))
    result = {name: analytics.balance(rows, start, cfg["prices"])
              for name, start in analytics.periods(time.time()).items()}
    result["amortisation"] = analytics.amortization(rows, cfg["prices"], cfg["system"]["cost"], config.commissioned(cfg))
    return result


@app.get("/")
def dashboard(request: Request, zeitraum: str = "tag"):
    cfg = config.load(request.app.state.config_path)
    storage = request.app.state.storage
    now = time.time()
    rows = storage.hourly(int(now))
    starts = analytics.periods(now)
    period = zeitraum if zeitraum in starts else "tag"
    latest = storage.latest()
    live = {k: v for k, (_, v) in latest.items()}
    live["pv"] = (live.get("pv_power") or 0) + (live.get("pv_ac_power") or 0) if latest else None
    hours = []
    for i in range(24):
        h0 = starts["tag"] + i * 3600
        b = analytics.balance([r for r in rows if r[1] < h0 + 3600], h0, cfg["prices"])
        hours.append({"label": i, "own": b["eigenverbrauch"] * 1000, "grid": b["netzbezug"] * 1000})
    peak = max(h["own"] + h["grid"] for h in hours)
    a = analytics.amortization(rows, cfg["prices"], cfg["system"]["cost"], config.commissioned(cfg))
    return templates.TemplateResponse(request, "dashboard.html", {
        "periods": PERIODS, "period": period, "b": analytics.balance(rows, starts[period], cfg["prices"]),
        "akku": analytics.battery(rows, starts[period], cfg["prices"], config.commissioned(cfg)),
        "live": live, "live_age": int(now - max(ts for ts, _ in latest.values())) if latest else None,
        "hours": hours, "peak": peak, "scale": 140 / peak if peak else 0, "a": a,
        "progress": min(a["bisher_gespart"] / a["kosten"] * 100, 100) if a["kosten"] else 0,
        "prices_set": cfg["prices"]["energy"] > 0 and cfg["system"]["cost"] > 0,
    })


@app.get("/nulleinspeisung")
def zero_feed_in(request: Request):
    cfg = config.load(request.app.state.config_path)
    storage = request.app.state.storage
    latest = {k: v for k, (_, v) in storage.latest().items()}
    since = int(time.time()) - 7 * 86400
    series = storage.series(since, ["grid_power", "output_power", "pv_ac_power", "battery_soc"])
    r = analytics.regulation(series, cfg["prices"], soc_min=latest.get("battery_soc_min") or 10,
                             limit=latest.get("output_power_limit") or 800)
    return templates.TemplateResponse(request, "regulation.html", {"r": r})


@app.get("/einstellungen")
def settings(request: Request):
    cfg = config.load(request.app.state.config_path)
    return templates.TemplateResponse(request, "settings.html", {"cfg": cfg})


@app.post("/einstellungen")
async def save_settings(request: Request):
    form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    cfg = config.load(request.app.state.config_path)
    try:
        values = {k: float(form[k].replace(",", ".")) for k in ("energy", "feed_in", "cost")}
        day = date.fromisoformat(form["commissioned"]) if form.get("commissioned") else None
        if min(values.values()) < 0 or (day and day > date.today()):
            raise ValueError
    except (KeyError, ValueError):
        return templates.TemplateResponse(request, "settings.html", {"cfg": cfg, "error": True}, status_code=400)
    cfg["prices"].update(energy=values["energy"], feed_in=values["feed_in"])
    cfg["system"].update(cost=values["cost"], commissioned=day)
    config.save(request.app.state.config_path, cfg)
    return RedirectResponse("/einstellungen?gespeichert=1", status_code=303)
