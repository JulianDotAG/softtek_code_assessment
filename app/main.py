from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import DomainError
from app.routers import customers, orders, reports, services

app = FastAPI(title="Customer, Service and Order API", version="1.0.0")


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    """One handler for every business rule: the exception knows its own status code."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(customers.router)
app.include_router(services.router)
app.include_router(orders.router)
app.include_router(reports.router)
