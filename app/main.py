from fastapi import FastAPI

app = FastAPI(title="Balkonaut")


@app.get("/api/health")
def health():
    return {"status": "ok"}
