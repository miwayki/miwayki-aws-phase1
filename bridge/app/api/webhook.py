from __future__ import annotations

"""Webhook Chatwoot. Extraído de main.py L350-576.

Refactorizado para usar módulos extraídos, pero con el MISMO comportamiento:
- Filtrado anti-loop
- Verificación de firma HMAC
- Intercepción de nota privada (seller feedback)
- Llamada a Langflow blocking
- Publicación de respuesta en Chatwoot
- Sync condicional de atributos, labels y contacto

Fase 2.5: session_repo (PG) reemplaza al dict en memoria para Langflow conversation_ids.
Fallback a dict en memoria si PG no está disponible.
"""

import json
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.config.settings import (
    BRIDGE_BUILD,
    CHATWOOT_API_TOKEN,
    CHATWOOT_BASE_URL,
    CHATWOOT_WEBHOOK_SECRET,
    BRIDGE_AUTO_REPLY,
    LANGFLOW_API_KEY,
    BRIDGE_SYNC_CHATWOOT_ATTRIBUTES,
)
from app.utils import safe_get
from app.utils.security import verify_chatwoot_webhook_signature, is_incoming_user_message
from app.adapters.chatwoot import (
    chatwoot_message_text,
    fetch_conversation,
    merge_custom_attributes,
    sync_labels,
    update_contact,
)
from app.adapters.langflow import blocking_reply
from app.domain.lead_scoring import heuristic_lead_signals
from app.repositories import session_repo
from app.utils.logging import log

router = APIRouter(tags=["webhook"])

# Fallback en memoria si PG no está disponible
_langflow_conversation_fallback: dict[str, str] = {}


@router.post("/webhooks/chatwoot")
async def chatwoot_webhook(request: Request) -> dict[str, Any]:
    raw_body = await request.body()
    verify_chatwoot_webhook_signature(raw_body, request, CHATWOOT_WEBHOOK_SECRET)
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido") from None
    event = payload.get("event")

    if event != "message_created":
        return {"ok": True, "ignored": True, "reason": "non_message_created_event"}

    account_id = safe_get(payload, "account", "id")
    conversation_id = safe_get(payload, "conversation", "id")

    if not account_id or not conversation_id:
        raise HTTPException(
            status_code=400,
            detail="Webhook sin account_id o conversation_id",
        )

    # Intercepción de Nota Privada de Agente (Seller Feedback)
    is_private = payload.get("private") is True
    sender_type = safe_get(payload, "sender", "type")
    if is_private and sender_type == "agent":
        note_text = chatwoot_message_text(payload)
        if note_text:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await merge_custom_attributes(
                    client, account_id, conversation_id,
                    {"pending_seller_feedback": note_text}
                )
            return {"ok": True, "note_captured": True}
        return {"ok": True, "ignored": True, "reason": "empty_private_note"}

    if not is_incoming_user_message(payload):
        return {"ok": True, "ignored": True, "reason": "not_incoming_user_message"}

    if not CHATWOOT_API_TOKEN:
        return {
            "ok": True,
            "ignored": True,
            "reason": "missing_chatwoot_api_token",
        }

    cw_cid = str(conversation_id)
    user_text = chatwoot_message_text(payload)
    if not user_text:
        return {"ok": True, "ignored": True, "reason": "empty_message_content"}

    consumed_feedback = None
    conv_data = None

    # Pre-fetch de conversación para extraer contexto de vendedor
    async with httpx.AsyncClient(timeout=15.0) as client:
        conv_data = await fetch_conversation(client, account_id, conversation_id)
        if conv_data:
            feedback = safe_get(conv_data, "custom_attributes", "pending_seller_feedback")
            if feedback and str(feedback).strip():
                consumed_feedback = str(feedback).strip()
                user_text = f"[CONTEXTO VENDEDOR]: {consumed_feedback}\n---\n{user_text}"

    if LANGFLOW_API_KEY:
        try:
            # Obtener session_id persistente (PG → fallback dict)
            try:
                prev_langflow_cid = await session_repo.get_langflow_conversation_id(int(cw_cid))
            except Exception:
                prev_langflow_cid = _langflow_conversation_fallback.get(cw_cid)

            langflow_result, new_langflow_cid = await blocking_reply(
                user_text, cw_cid, langflow_conversation_id=prev_langflow_cid
            )
            log.info(f"DEBUG LANGFLOW RAW RESULT: {langflow_result}")
            if new_langflow_cid:
                try:
                    await session_repo.set_langflow_conversation_id(int(cw_cid), new_langflow_cid)
                except Exception:
                    _langflow_conversation_fallback[cw_cid] = new_langflow_cid
                    log.warning("session_repo_fallback: using in-memory for conv=%s", cw_cid)
            reply_text = langflow_result.get("reply_text") or "..."
            source = "langflow"
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Error llamando a Langflow: {exc}",
            ) from exc
    else:
        langflow_result = {"reply_text": BRIDGE_AUTO_REPLY}
        reply_text = BRIDGE_AUTO_REPLY
        source = "static_auto_reply"

    msg_url = (
        f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}"
        f"/conversations/{conversation_id}/messages"
    )
    msg_body = {"content": reply_text, "message_type": "outgoing", "private": False}
    headers = {"api_access_token": CHATWOOT_API_TOKEN}

    http_timeout = 30.0 if BRIDGE_SYNC_CHATWOOT_ATTRIBUTES else 15.0
    attr_report: dict[str, Any] | None = None
    contact_report: dict[str, Any] | None = None
    lead: dict[str, Any] | None = None
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        response = await client.post(msg_url, json=msg_body, headers=headers)

        if response.status_code >= 300:
            raise HTTPException(
                status_code=502,
                detail=f"Error al publicar mensaje en Chatwoot: {response.text}",
            )

        if BRIDGE_SYNC_CHATWOOT_ATTRIBUTES:
            try:
                # Fallback heurístico si Langflow no entrega campos estructurados
                fallback = heuristic_lead_signals(user_text, ai_source=source)

                langflow_score = langflow_result.get("lead_score")
                langflow_temp = langflow_result.get("lead_temperature")
                langflow_handoff = langflow_result.get("handoff_recommended")
                langflow_summary = langflow_result.get("reasoning_summary")

                final_score = langflow_score if isinstance(langflow_score, int) else fallback["lead_score"]
                final_temp = langflow_temp if isinstance(langflow_temp, str) else fallback["lead_temperature"]
                final_handoff = langflow_handoff if isinstance(langflow_handoff, bool) else fallback["handoff_recommended"]

                if isinstance(langflow_summary, str) and langflow_summary.strip():
                    summary = langflow_summary.strip()
                else:
                    summary = reply_text.strip().replace("\n", " ")

                if len(summary) > 280:
                    summary = summary[:277] + "..."

                lead = {
                    "lead_score": final_score,
                    "lead_temperature": final_temp,
                    "handoff_recommended": final_handoff,
                }

                updates: dict[str, Any] = {
                    "lead_score": final_score,
                    "lead_temperature": final_temp,
                    "handoff_recommended": final_handoff,
                    "last_ai_summary": summary,
                    "ai_source": source,
                    "miwayki_bridge_build": BRIDGE_BUILD,
                }

                # Consumir el feedback si fue inyectado en este turno
                if consumed_feedback:
                    updates["pending_seller_feedback"] = None

                # 1. Persistencia de atributos de conversación
                try:
                    attr_report = await merge_custom_attributes(
                        client,
                        account_id,
                        conversation_id,
                        updates,
                        prev_conv=conv_data,
                    )
                except Exception as e:
                    attr_report = {"ok": False, "error": f"Conv Attr Error: {e}"}

                # 2. Sincronización de Contacto (Whitelist mapping - Isolada)
                contact_report = {"status": "started"}
                try:
                    extracted = langflow_result.get("extracted_fields")
                    contact_id = safe_get(conv_data, "meta", "sender", "id")

                    if not contact_id:
                        contact_report = {"status": "skipped", "reason": "no_contact_id_in_conv"}
                    elif not isinstance(extracted, dict):
                        contact_report = {"status": "skipped", "reason": "extracted_fields_not_dict"}
                    else:
                        c_update: dict[str, Any] = {}

                        # Mapeo Whitelist Expandido (§33.1)
                        # Name fallback
                        val_name = extracted.get("name") or extracted.get("customer_name")
                        if val_name:
                            c_update["name"] = str(val_name).strip()

                        # Email
                        if extracted.get("email"):
                            c_update["email"] = str(extracted["email"]).strip()

                        # Phone: Validar E.164 (debe empezar con +) para evitar Error 422
                        val_phone = str(extracted.get("phone", "")).strip()
                        if val_phone.startswith("+") and len(val_phone) >= 8:
                            c_update["phone_number"] = val_phone

                        # Atributos personalizados (Whitelist §33.1)
                        c_attrs: dict[str, Any] = {}
                        if extracted.get("destination"):
                            c_attrs["travel_destination"] = str(extracted["destination"]).strip()

                        # Travel dates fallback
                        val_dates = extracted.get("travel_dates") or extracted.get("travel_date")
                        if val_dates:
                            c_attrs["travel_dates"] = str(val_dates).strip()

                        if c_attrs:
                            c_update["custom_attributes"] = c_attrs

                        if c_update:
                            contact_report = await update_contact(client, account_id, contact_id, c_update)
                        else:
                            contact_report = {"status": "skipped", "reason": "no_whitelisted_data"}
                except Exception as e:
                    contact_report = {"ok": False, "error": f"Contact Sync Error: {e}"}

                # 3. Sincronización de etiqueta "hot" (Isolada)
                try:
                    await sync_labels(
                        client,
                        account_id,
                        conversation_id,
                        add_labels=["hot"] if final_score >= 70 else None,
                        remove_labels=["hot"] if final_score < 70 else None,
                        prev_conv=conv_data,
                    )
                except Exception:
                    pass
            except Exception as e:
                # Fallo catastrófico en la preparación de datos de sync
                if attr_report is None:
                    attr_report = {"ok": False, "error": str(e)}

    out: dict[str, Any] = {
        "ok": True,
        "replied": True,
        "conversation_id": conversation_id,
        "source": source,
    }
    if lead is not None:
        out["lead"] = lead
    if attr_report is not None:
        out["chatwoot_custom_attributes"] = attr_report
    if contact_report is not None:
        out["chatwoot_contact_sync"] = contact_report
    return out
