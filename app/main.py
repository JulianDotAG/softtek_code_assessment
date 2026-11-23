from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import ConflictError, NotFoundError
from app.routers import customers, orders, reports, services

app = FastAPI(title="Customer, Service and Order API", version="1.0.0")


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.detail})


@app.exception_handler(ConflictError)
async def conflict_handler(_: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": exc.detail})


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(customers.router)
app.include_router(services.router)
app.include_router(orders.router)
app.include_router(reports.router)
