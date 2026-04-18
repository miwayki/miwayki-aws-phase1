from __future__ import annotations

"""POST /lead/upsert — Registro y enriquecimiento de leads."""

from typing import Any

from fastapi import APIRouter

from app.schemas.lead import LeadUpsertRequest, LeadResponse
from app.repositories import lead_repo
from app.utils.logging import log

router = APIRouter(tags=["lead"])

UPDATABLE_FIELDS = [
    "customer_name", "customer_email", "customer_phone",
    "destination", "travel_dates", "party_size", "group_type",
    "budget_range", "urgency", "special_requirements",
]


@router.post("/lead/upsert", response_model=LeadResponse)
async def upsert_lead(req: LeadUpsertRequest) -> Any:
    """Crea un lead nuevo o actualiza los campos proporcionados.

    Langflow llama este endpoint progresivamente a medida que extrae datos
    del usuario durante la conversación.
    """
    update_fields = {}
    fields_updated = []
    for field_name in UPDATABLE_FIELDS:
        val = getattr(req, field_name, None)
        if val is not None:
            update_fields[field_name] = val
            fields_updated.append(field_name)

    c_id = req.conversation_id if req.conversation_id is not None else 1
    result = await lead_repo.upsert_lead(c_id, **update_fields)

    log.info(
        "lead_upserted: conversation=%d lead=%d is_new=%s fields=%s",
        c_id, result["lead_id"], result["is_new"], fields_updated,
    )

    return LeadResponse(
        lead_id=result["lead_id"],
        conversation_id=c_id,
        commercial_state=result["commercial_state"],
        is_new=result["is_new"],
        fields_updated=fields_updated,
    )
