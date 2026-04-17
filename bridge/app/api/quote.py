from __future__ import annotations

"""POST /quote/calculate — Motor de cotización."""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.quote import QuoteRequest, QuoteResponse, QuoteBreakdownResponse
from app.schemas.common import ErrorResponse
from app.adapters import nocodb
from app.adapters.nocodb import CatalogUnavailableError
from app.domain import pricing
from app.domain.handoff import evaluate_handoff
from app.domain.state_machine import can_transition
from app.repositories import lead_repo, quote_repo
from app.config.settings import QUOTE_VALIDITY_DAYS
from app.utils.logging import log

router = APIRouter(tags=["quote"])


@router.post(
    "/quote/calculate",
    response_model=QuoteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Tour no encontrado"},
        422: {"description": "Validación fallida"},
        503: {"model": ErrorResponse, "description": "Catálogo no disponible"},
    },
)
async def calculate_quote(req: QuoteRequest) -> Any:
    """Calcula una cotización completa basada en el catálogo NocoDB."""

    # Validación: fecha no en el pasado
    if req.travel_date < date.today():
        raise HTTPException(422, detail="La fecha de viaje no puede ser en el pasado")

    # Obtener tour del catálogo
    try:
        tour = await nocodb.get_tour(req.tour_code)
    except CatalogUnavailableError:
        raise HTTPException(503, detail="El sistema de catálogo no está disponible")

    if tour is None:
        # Tour no encontrado — evaluar handoff
        available = await nocodb.list_tours()
        codes = [t.get("code", "") for t in available]
        raise HTTPException(404, detail={
            "error": "tour_not_found",
            "message": f"No encontramos el tour '{req.tour_code}'.",
            "available_tours": codes,
        })

    # Obtener datos para el cálculo
    variant = None
    if req.variant_code:
        variant = await nocodb.get_variant(req.tour_code, req.variant_code)

    season = await nocodb.get_season_for_date(req.travel_date)
    holiday = await nocodb.get_holiday_for_date(req.travel_date)
    rules = await nocodb.list_pricing_rules(req.party_size, req.group_type.value)
    exceptions = await nocodb.list_exceptions(req.tour_code, req.travel_date)

    # Calcular cotización
    breakdown = pricing.calculate_quote(
        tour=tour,
        variant=variant,
        travel_date=req.travel_date,
        party_size=req.party_size,
        group_type=req.group_type.value,
        season=season,
        holiday=holiday,
        pricing_rules=rules,
        exceptions=exceptions,
    )

    # Persist: upsert lead + crear quote
    lead = await lead_repo.upsert_lead(
        req.conversation_id,
        destination=req.tour_code,
        party_size=req.party_size,
        group_type=req.group_type.value,
        travel_dates=str(req.travel_date),
    )
    quote_id = await quote_repo.create_quote(lead["lead_id"], breakdown)

    # State transition: new_inquiry → quoted (o quoted → quoted para re-cotizar)
    if can_transition(lead["commercial_state"], "quoted"):
        await lead_repo.update_state(lead["lead_id"], "quoted")
    await lead_repo.update_lead_fields(lead["lead_id"], last_quote_id=quote_id)

    # Handoff evaluation
    handoff = evaluate_handoff(
        party_size=req.party_size,
        group_type=req.group_type.value,
        travel_date=req.travel_date,
        tour_found=True,
    )

    valid_until = (datetime.now(timezone.utc) + timedelta(days=QUOTE_VALIDITY_DAYS)).isoformat()

    log.info(
        "quote_calculated: conversation=%d quote=%d total=%.2f handoff=%s",
        req.conversation_id, quote_id, float(breakdown.total_price_pen), handoff.required,
    )

    return QuoteResponse(
        quote_id=quote_id,
        tour_name=breakdown.tour_name,
        variant_name=breakdown.variant_name,
        travel_date=str(breakdown.travel_date),
        party_size=breakdown.party_size,
        breakdown=QuoteBreakdownResponse(
            base_price_per_person=float(breakdown.base_price_per_person),
            base_total=float(breakdown.base_total),
            season_name=breakdown.season_name,
            season_adjustment=float(breakdown.season_adjustment),
            holiday_name=breakdown.holiday_name,
            holiday_adjustment=float(breakdown.holiday_adjustment),
            group_adjustment=float(breakdown.group_adjustment),
            group_rules_applied=breakdown.group_rules_applied,
            exception_adjustment=float(breakdown.exception_adjustment),
            exceptions_applied=breakdown.exceptions_applied,
            total_price_pen=float(breakdown.total_price_pen),
            per_person_pen=float(breakdown.per_person_pen),
        ),
        valid_until=valid_until,
        message=(
            f"Cotización generada. Precio total: S/ {breakdown.total_price_pen:,.2f} "
            f"(S/ {breakdown.per_person_pen:,.2f} por persona)."
        ),
        handoff_triggered=handoff.required,
        handoff_reason=handoff.reason,
    )
