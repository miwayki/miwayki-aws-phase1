from __future__ import annotations

"""Adaptador Chatwoot. Extraído de main.py L90-258 sin cambios funcionales."""

import json
from typing import Any

import httpx

from app.config.settings import CHATWOOT_BASE_URL, CHATWOOT_API_TOKEN
from app.utils.logging import log


def chatwoot_message_text(payload: dict[str, Any]) -> str:
    """Extrae el texto del mensaje del payload del webhook.
    Extraído de main.py L90-96.
    """
    raw = payload.get("content")
    if raw is None and isinstance(payload.get("message"), dict):
        raw = payload["message"].get("content")
    if raw is None:
        return ""
    return str(raw).strip()


async def fetch_conversation(
    client: httpx.AsyncClient,
    account_id: Any,
    conversation_id: Any,
) -> dict[str, Any] | None:
    """GET conversación Chatwoot. Extraído de main.py L152-168."""
    url = (
        f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}"
        f"/conversations/{conversation_id}"
    )
    r = await client.get(url, headers={"api_access_token": CHATWOOT_API_TOKEN})
    if r.status_code >= 300:
        return None
    try:
        data = r.json()
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


async def merge_custom_attributes(
    client: httpx.AsyncClient,
    account_id: Any,
    conversation_id: Any,
    updates: dict[str, Any],
    prev_conv: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """GET + POST para no pisar atributos ya existentes. Extraído de main.py L171-198."""
    prev = prev_conv or await fetch_conversation(client, account_id, conversation_id)
    existing_raw = (prev or {}).get("custom_attributes")
    existing: dict[str, Any] = existing_raw if isinstance(existing_raw, dict) else {}
    merged = {**existing, **updates}
    url = (
        f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}"
        f"/conversations/{conversation_id}/custom_attributes"
    )
    r = await client.post(
        url,
        headers={"api_access_token": CHATWOOT_API_TOKEN},
        json={"custom_attributes": merged},
    )
    if r.status_code >= 300:
        return {
            "ok": False,
            "http_status": r.status_code,
            "detail": r.text[:400],
        }
    return {"ok": True, "http_status": r.status_code}


async def sync_labels(
    client: httpx.AsyncClient,
    account_id: Any,
    conversation_id: Any,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
    prev_conv: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """GET + POST para añadir/quitar etiquetas sin pisar el resto.
    Extraído de main.py L201-236.
    """
    prev = prev_conv or await fetch_conversation(client, account_id, conversation_id)
    existing: list[str] = (prev or {}).get("labels") or []

    current_set = set(existing)
    if add_labels:
        current_set.update(add_labels)
    if remove_labels:
        current_set.difference_update(remove_labels)

    merged = list(current_set)

    url = (
        f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}"
        f"/conversations/{conversation_id}/labels"
    )
    r = await client.post(
        url,
        headers={"api_access_token": CHATWOOT_API_TOKEN},
        json={"labels": merged},
    )
    if r.status_code >= 300:
        return {
            "ok": False,
            "http_status": r.status_code,
            "detail": r.text[:400],
        }
    return {"ok": True, "labels": merged}


async def update_contact(
    client: httpx.AsyncClient,
    account_id: Any,
    contact_id: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """PATCH para actualizar datos de contacto. Extraído de main.py L239-258."""
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}/contacts/{contact_id}"
    r = await client.patch(
        url,
        headers={"api_access_token": CHATWOOT_API_TOKEN},
        json=payload,
    )
    if r.status_code >= 300:
        return {
            "ok": False,
            "http_status": r.status_code,
            "detail": r.text[:400],
        }
    return {"ok": True, "http_status": r.status_code}


async def send_message(
    client: httpx.AsyncClient,
    account_id: Any,
    conversation_id: Any,
    content: str,
    *,
    private: bool = False,
) -> dict[str, Any]:
    """Publish a message to a Chatwoot conversation."""
    url = (
        f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}"
        f"/conversations/{conversation_id}/messages"
    )
    body = {"content": content, "message_type": "outgoing", "private": private}
    r = await client.post(
        url,
        headers={"api_access_token": CHATWOOT_API_TOKEN},
        json=body,
    )
    if r.status_code >= 300:
        log.error(
            "chatwoot_send_message_failed: status=%d body=%s",
            r.status_code,
            r.text[:400],
        )
        return {"ok": False, "http_status": r.status_code}
    return {"ok": True, "http_status": r.status_code}
