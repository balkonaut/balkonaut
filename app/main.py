from fastapi import FastAPI

app = FastAPI(title="BalkonBilanz")


@app.get("/api/health")
def health():
    return {"status": "ok"}
