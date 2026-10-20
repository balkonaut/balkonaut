import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config
from balkonaut import collector
from balkonaut.homeassistant import HomeAssistant
from balkonaut.storage import Storage

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(app):
    data = Path(os.environ.get("BALKONAUT_DATA", "data"))
    data.mkdir(parents=True, exist_ok=True)
    app.state.config_path = data / "config.yaml"
    cfg = config.load(app.state.config_path)
    task = None
    if ha := cfg.get("home_assistant"):
        adapter = HomeAssistant(ha["url"], ha["token"], {k: tuple(v) for k, v in ha["entities"].items()})
        task = asyncio.create_task(collector.run(adapter, Storage(data / "balkonaut.db")))
    yield
    if task:
        task.cancel()


app = FastAPI(title="Balkonaut", lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"status": "ok"}


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
        if min(values.values()) < 0:
            raise ValueError
    except (KeyError, ValueError):
        return templates.TemplateResponse(request, "settings.html", {"cfg": cfg, "error": True}, status_code=400)
    cfg["prices"].update(energy=values["energy"], feed_in=values["feed_in"])
    cfg["system"]["cost"] = values["cost"]
    config.save(request.app.state.config_path, cfg)
    return RedirectResponse("/einstellungen?gespeichert=1", status_code=303)
