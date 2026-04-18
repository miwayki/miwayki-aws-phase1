"""MiWayki Bridge — App Factory (Fase 2.5 hardened).

Refactorizado desde monolito main.py v0.10 (577 líneas) a estructura por capas.
Toda la lógica está en app/api/, app/domain/, app/adapters/, etc.
Este archivo solo crea la app FastAPI e incluye los routers.

Backup del monolito original: main.py.bak-v010
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.config.settings import BRIDGE_BUILD, BRIDGE_DATABASE_URL
from app.utils.logging import log


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator:
    """Lifecycle: inicializa DB pool al arrancar, lo cierra al apagar."""
    if BRIDGE_DATABASE_URL:
        try:
            from app.repositories.database import get_pool, close_pool
            await get_pool()
            log.info("lifespan_startup: database pool ready")
        except Exception as exc:
            log.warning("lifespan_startup: database pool NOT available (%s) — endpoints PG fallarán", exc)
    else:
        log.info("lifespan_startup: BRIDGE_DATABASE_URL not set — running without PG")
    yield
    # Shutdown
    try:
        from app.repositories.database import close_pool
        await close_pool()
        log.info("lifespan_shutdown: database pool closed")
    except Exception:
        pass


from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(title="Miwayki Bridge", version="2.0.0", lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    log.error(f"422 Validation Error on {request.url.path}: {exc.errors()} body={exc.body}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

log.info("bridge_starting build=%s", BRIDGE_BUILD)

# ── Incluir routers ──────────────────────────────────────────────────────
from app.api.health import router as health_router
from app.api.webhook import router as webhook_router

app.include_router(health_router)
app.include_router(webhook_router)

# ── Routers de Fase 2 ────────────────────────────────────────────────────
from app.api.catalog import router as catalog_router
from app.api.quote import router as quote_router
from app.api.lead import router as lead_router
from app.api.reservation import router as reservation_router

app.include_router(catalog_router)
app.include_router(quote_router)
app.include_router(lead_router)
app.include_router(reservation_router)
