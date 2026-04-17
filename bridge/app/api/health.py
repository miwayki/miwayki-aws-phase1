"""Endpoints de salud. Extraídos de main.py L316-347 + NocoDB (Fase 2.1)."""

from typing import Any

from fastapi import APIRouter

from app.config.settings import BRIDGE_BUILD
from app.adapters import langflow, nocodb

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "bridge_build": BRIDGE_BUILD,
        "endpoints": [
            "/health",
            "/health/langflow",
            "/health/nocodb",
            "/webhooks/chatwoot",
            "/catalog/tours",
            "/quote/calculate",
            "/lead/upsert",
            "/reservation/payment-instructions",
            "/reservation/voucher",
        ],
    }


@router.get("/health/langflow")
async def health_langflow() -> dict[str, Any]:
    """Comprueba red hasta el contenedor `api` de Langflow (no usa la app API key)."""
    return await langflow.check_health()


@router.get("/health/nocodb")
async def health_nocodb() -> dict[str, Any]:
    """Comprueba conectividad con NocoDB (catálogo comercial)."""
    return await nocodb.check_health()
