from __future__ import annotations

"""Adaptador Langflow.

Interactúa con la API de ejecución de flujos de Langflow.
"""

import json
from typing import Any

import httpx

from app.config.settings import LANGFLOW_API_BASE, LANGFLOW_API_KEY, LANGFLOW_FLOW_ID
from app.utils.logging import log


def _langflow_service_root() -> str:
    """Raíz HTTP del servicio API de Langflow."""
    base = LANGFLOW_API_BASE.rstrip("/")
    if base.endswith("/api/v1"):
        return base[: -len("/api/v1")].rstrip("/") or base
    return base


async def blocking_reply(
    query: str,
    chatwoot_conversation_id: str,
    langflow_conversation_id: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    """POST /run/{flow_id} en modo blocking.

    Retorna (parsed_result, new_langflow_conversation_id).
    """
    if not LANGFLOW_API_KEY or not LANGFLOW_FLOW_ID:
        raise RuntimeError("LANGFLOW_API_KEY o LANGFLOW_FLOW_ID no configurada")

    url = f"{LANGFLOW_API_BASE}/run/{LANGFLOW_FLOW_ID}"
    headers = {
        "x-api-key": LANGFLOW_API_KEY,
        "Content-Type": "application/json",
    }
    session_id = langflow_conversation_id or f"cw2-{chatwoot_conversation_id}"
    body: dict[str, Any] = {
        "input_value": query,
        "input_type": "chat",
        "output_type": "chat",
        "session_id": session_id,
        "tweaks": {}
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=body, headers=headers)

    if response.status_code >= 300:
        raise RuntimeError(
            f"Langflow HTTP {response.status_code}: {response.text[:500]}"
        )

    data = response.json()
    new_cid_out = session_id

    try:
        raw_answer = data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(
            f"Respuesta Langflow sin formato esperado: {str(data)[:300]}"
        )

    raw_answer = raw_answer.strip()
    
    # Intento de parseo JSON para contrato estructurado (§12.3)
    try:
        parsed = json.loads(raw_answer)
        if isinstance(parsed, dict) and "reply_text" in parsed:
            return parsed, new_cid_out
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: tratar la respuesta como texto plano
    return {"reply_text": raw_answer}, new_cid_out


async def check_health() -> dict[str, Any]:
    """Verifica conectividad al servicio API de Langflow."""
    root = _langflow_service_root()
    url = f"{root}/health"
    out: dict[str, Any] = {
        "langflow_service_url": root,
        "ping_url": url,
        "app_key_configured": bool(LANGFLOW_API_KEY),
        "flow_id_configured": bool(LANGFLOW_FLOW_ID),
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url)
        out["http_status"] = r.status_code
        out["reachable"] = r.status_code < 500
        try:
            out["langflow_health"] = r.json()
        except json.JSONDecodeError:
            out["langflow_health_preview"] = r.text[:200]
    except httpx.RequestError as exc:
        out["reachable"] = False
        out["error"] = str(exc)[:400]
    return out
