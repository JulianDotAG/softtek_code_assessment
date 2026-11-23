from fastapi import FastAPI

app = FastAPI(title="Customer, Service and Order API", version="1.0.0")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
