from __future__ import annotations

"""GET /catalog/tours — Catálogo de tours desde NocoDB."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas.catalog import CatalogResponse, TourItem, VariantItem
from app.adapters import nocodb
from app.adapters.nocodb import CatalogUnavailableError
from app.utils.logging import log

router = APIRouter(tags=["catalog"])


@router.get("/catalog/tours", response_model=CatalogResponse,
            responses={503: {"description": "NocoDB no disponible"}})
async def list_tours(active_only: bool = Query(True, description="Filtrar solo tours activos")) -> Any:
    """Lista todos los tours disponibles en el catálogo NocoDB con sus variantes."""
    try:
        tours_raw = await nocodb.list_tours(active_only=active_only)
    except CatalogUnavailableError as exc:
        raise HTTPException(503, detail=f"Catálogo no disponible: {exc}")

    tours = []
    for t in tours_raw:
        tour_code = t.get("code", "")
        try:
            variants_raw = await nocodb.list_variants(tour_code, active_only=active_only)
        except CatalogUnavailableError:
            variants_raw = []

        variants = [
            VariantItem(
                code=v.get("code", ""),
                name=v.get("name", ""),
                price_adjustment_pen=float(v.get("price_adjustment_pen", 0)),
                duration_days=v.get("duration_days"),
            )
            for v in variants_raw
        ]

        tours.append(TourItem(
            code=tour_code,
            name=t.get("name", ""),
            description=t.get("description"),
            base_price_pen=float(t.get("base_price_pen", 0)),
            duration_days=int(t.get("duration_days", 0)),
            min_pax=int(t.get("min_pax", 1)),
            max_pax=int(t.get("max_pax", 30)),
            includes=t.get("includes"),
            excludes=t.get("excludes"),
            variants=variants,
        ))

    log.info("catalog_listed: tours=%d active_only=%s", len(tours), active_only)

    return CatalogResponse(tours=tours, count=len(tours))
