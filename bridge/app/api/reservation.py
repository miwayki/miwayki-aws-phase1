from __future__ import annotations

"""Endpoints de reservación y pago (Fase 2.4).

POST /reservation/payment-instructions
  - Valida cotización activa y no expirada
  - Transiciona quoted → awaiting_payment
  - Crea reserva en PG
  - Retorna cuentas bancarias desde NocoDB

POST /reservation/voucher
  - Registra comprobante de pago
  - Transiciona awaiting_payment → voucher_received
  - Dispara handoff obligatorio (regla de negocio no negociable)
"""

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.reservation import (
    PaymentInstructionsRequest,
    PaymentInstructionsResponse,
    BankAccountInfo,
    VoucherRequest,
    VoucherResponse,
)
from app.adapters import nocodb
from app.domain.state_machine import validate_transition, InvalidTransitionError
from app.repositories import lead_repo, quote_repo
from app.repositories.database import get_pool
from app.utils.logging import log

router = APIRouter(tags=["reservation"])


@router.post(
    "/reservation/payment-instructions",
    response_model=PaymentInstructionsResponse,
    responses={
        404: {"description": "Lead o cotización no encontrada"},
        409: {"description": "Transición de estado no válida"},
        503: {"description": "Sin cuentas bancarias configuradas"},
    },
)
async def payment_instructions(req: PaymentInstructionsRequest) -> Any:
    """Genera instrucciones de pago para una cotización aceptada.

    Flujo: el usuario acepta la cotización → Langflow llama este endpoint →
    Bridge retorna datos bancarios → Langflow muestra al usuario.
    """
    # Validar que el lead existe
    lead = await lead_repo.get_lead_by_conversation(req.conversation_id)
    if not lead:
        raise HTTPException(404, detail="Lead no encontrado para esta conversación")

    # Validar cotización activa y no expirada
    quote = await quote_repo.get_active_quote(req.quote_id)
    if not quote:
        raise HTTPException(
            404,
            detail="Cotización no encontrada o expirada. Por favor genere una nueva cotización.",
        )

    # Validar transición de estado: quoted → awaiting_payment
    try:
        validate_transition(lead["commercial_state"], "awaiting_payment")
    except InvalidTransitionError:
        raise HTTPException(
            409,
            detail=(
                f"No se puede solicitar instrucciones de pago en estado "
                f"'{lead['commercial_state']}'. Se requiere estado 'quoted'."
            ),
        )

    # Obtener cuentas bancarias desde NocoDB
    bank_accounts = await nocodb.list_bank_accounts(currency=req.currency)
    if not bank_accounts:
        raise HTTPException(
            503,
            detail="No hay cuentas bancarias configuradas en el catálogo",
        )

    # Crear reserva en PostgreSQL
    pool = await get_pool()
    reservation_id = await pool.fetchval(
        """
        INSERT INTO bridge.reservations
            (lead_id, quote_id, status, payment_amount, payment_currency, bank_account_info)
        VALUES ($1, $2, 'pending', $3, $4, $5)
        RETURNING id
        """,
        lead["id"],
        req.quote_id,
        float(quote["total_price_pen"]),
        req.currency,
        json.dumps([
            {
                "bank_name": b.get("bank_name"),
                "account_number": b.get("account_number"),
            }
            for b in bank_accounts
        ]),
    )

    # Transicionar estado: quoted → awaiting_payment
    await lead_repo.update_state(lead["id"], "awaiting_payment")

    amount = float(quote["total_price_pen"])
    accounts = [
        BankAccountInfo(
            bank_name=b.get("bank_name", ""),
            account_holder=b.get("account_holder", ""),
            account_number=b.get("account_number", ""),
            cci=b.get("cci"),
            account_type=b.get("account_type", ""),
            currency=b.get("currency", "PEN"),
        )
        for b in bank_accounts
    ]

    log.info(
        "payment_instructions_sent: conversation=%d reservation=%d amount=%.2f",
        req.conversation_id, reservation_id, amount,
    )

    return PaymentInstructionsResponse(
        reservation_id=reservation_id,
        amount=amount,
        currency=req.currency,
        bank_accounts=accounts,
        instructions=(
            f"Realice una transferencia por S/ {amount:,.2f} a la cuenta indicada. "
            f"Una vez completada, envíe el comprobante de pago por este mismo chat."
        ),
        commercial_state="awaiting_payment",
    )


@router.post(
    "/reservation/voucher",
    response_model=VoucherResponse,
    responses={
        404: {"description": "Lead no encontrado"},
        409: {"description": "Transición de estado no válida"},
    },
)
async def register_voucher(req: VoucherRequest) -> Any:
    """Registra un comprobante de pago y activa handoff obligatorio.

    Flujo: el usuario envía comprobante → Langflow detecta voucher → llama este
    endpoint → Bridge registra y escala a humano en Chatwoot.
    """
    # Validar que el lead existe
    lead = await lead_repo.get_lead_by_conversation(req.conversation_id)
    if not lead:
        raise HTTPException(404, detail="Lead no encontrado para esta conversación")

    # Validar transición: awaiting_payment → voucher_received
    try:
        validate_transition(lead["commercial_state"], "voucher_received")
    except InvalidTransitionError:
        raise HTTPException(
            409,
            detail=(
                f"No se puede registrar voucher en estado '{lead['commercial_state']}'. "
                f"Se requiere estado 'awaiting_payment'."
            ),
        )

    # Actualizar la reserva pendiente con el voucher
    pool = await get_pool()
    updated = await pool.fetchval(
        """
        UPDATE bridge.reservations
        SET status = 'voucher_received',
            voucher_reference = $1,
            voucher_received_at = NOW(),
            updated_at = NOW()
        WHERE lead_id = $2 AND status = 'pending'
        RETURNING id
        """,
        req.voucher_reference or "",
        lead["id"],
    )

    reservation_id = updated if updated else 0

    # Transicionar estado: awaiting_payment → voucher_received
    await lead_repo.update_state(lead["id"], "voucher_received")

    # Marcar handoff obligatorio
    await lead_repo.update_lead_fields(
        lead["id"],
        handoff_required=True,
        handoff_reason="Voucher recibido — requiere verificación humana",
    )

    log.info(
        "voucher_registered: conversation=%d reservation=%d voucher_ref=%s",
        req.conversation_id, reservation_id, req.voucher_reference,
    )

    return VoucherResponse(
        reservation_id=reservation_id,
        commercial_state="voucher_received",
        message=(
            "Comprobante registrado exitosamente. Nuestro equipo verificará "
            "el pago y confirmará su reserva a la brevedad."
        ),
    )
