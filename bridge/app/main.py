import hashlib
import hmac
import json
import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request

# Cambia cuando quieras comprobar desde fuera si el proceso en :8000 es imagen nueva o vieja.
BRIDGE_BUILD = "0.4-minimal-default"

app = FastAPI(title="Miwayki Bridge", version="0.4.0")

CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "http://chatwoot:3000")
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "")
CHATWOOT_WEBHOOK_SECRET = os.getenv("CHATWOOT_WEBHOOK_SECRET", "").strip()
BRIDGE_AUTO_REPLY = os.getenv(
    "BRIDGE_AUTO_REPLY",
    "Recibido. Este es el bridge MVP de prueba conectado correctamente.",
)
# Base URL del API de Dify (desde el contenedor bridge: servicio Docker "api", puerto 5001).
DIFY_API_BASE = os.getenv("DIFY_API_BASE", "http://api:5001/v1").rstrip("/")
DIFY_API_KEY = os.getenv("DIFY_API_KEY", "").strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw == "":
        return default
    return raw in ("1", "true", "yes", "on", "y")


# Desactivado por defecto: prioridad = validar envío/recepción Dify ↔ Chatwoot. Activar con 1 cuando el puente básico funcione.
BRIDGE_SYNC_CHATWOOT_ATTRIBUTES = _env_bool("BRIDGE_SYNC_CHATWOOT_ATTRIBUTES", False)

# Memoria MVP: conversación Chatwoot -> conversation_id de Dify (se pierde al reiniciar el bridge).
_dify_conversation_by_chatwoot: dict[str, str] = {}


def _safe_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _is_incoming_user_message(payload: dict[str, Any]) -> bool:
    message_type = _safe_get(payload, "message_type")
    sender_type = _safe_get(payload, "sender", "type")

    # Evita loops: solo procesar mensajes entrantes de contacto/usuario.
    if sender_type and str(sender_type).lower() in {"agent", "bot"}:
        return False
    if message_type and str(message_type).lower() in {"outgoing", "template"}:
        return False
    return True


def _verify_chatwoot_webhook_signature(raw_body: bytes, request: Request) -> None:
    """Valida X-Chatwoot-Signature según documentación oficial (timestamp + cuerpo crudo)."""
    if not CHATWOOT_WEBHOOK_SECRET:
        return
    received = request.headers.get("X-Chatwoot-Signature", "")
    ts_header = request.headers.get("X-Chatwoot-Timestamp", "")
    if not received or not ts_header:
        raise HTTPException(status_code=401, detail="Faltan headers de firma del webhook")
    try:
        ts = int(ts_header)
    except ValueError:
        raise HTTPException(status_code=401, detail="Timestamp de firma inválido")
    if abs(int(time.time()) - ts) > 300:
        raise HTTPException(status_code=401, detail="Webhook demasiado antiguo (replay)")
    signed_string = f"{ts}.{raw_body.decode('utf-8')}"
    expected = (
        "sha256="
        + hmac.new(
            CHATWOOT_WEBHOOK_SECRET.encode("utf-8"),
            signed_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail="Firma de webhook inválida")


def _chatwoot_message_text(payload: dict[str, Any]) -> str:
    raw = payload.get("content")
    if raw is None and isinstance(payload.get("message"), dict):
        raw = payload["message"].get("content")
    if raw is None:
        return ""
    return str(raw).strip()


def _heuristic_lead_signals(user_text: str, *, ai_source: str) -> dict[str, Any]:
    """MVP alineado a §13 (umbrales) hasta que Dify devuelva JSON estructurado (§12.3)."""
    t = user_text.lower()
    hot_kw = (
        "precio",
        "reserva",
        "pago",
        "teléfono",
        "telefono",
        "whatsapp",
        "correo",
        "email",
        "@",
        "fecha",
        "disponib",
        "cierre",
        "contacto",
        "llamada",
        "llámame",
        "reservar",
        "comprar",
        "tarjeta",
    )
    warm_kw = (
        "cuándo",
        "cuando",
        "dónde",
        "donde",
        "opciones",
        "paquete",
        "tour",
        "viaje",
        "presupuesto",
        "interesado",
        "información",
        "informacion",
    )
    score, temp, handoff = 25, "cold", False
    if any(k in t for k in hot_kw):
        score, temp, handoff = 78, "hot", True
    elif len(t) > 100 or any(k in t for k in warm_kw):
        score, temp, handoff = 52, "warm", False
    if ai_source == "static_auto_reply":
        score = min(score, 35)
        temp = "cold"
        handoff = False
    return {
        "lead_score": score,
        "lead_temperature": temp,
        "handoff_recommended": handoff,
    }


async def _chatwoot_fetch_conversation(
    client: httpx.AsyncClient,
    account_id: Any,
    conversation_id: Any,
) -> dict[str, Any] | None:
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


async def _chatwoot_merge_custom_attributes(
    client: httpx.AsyncClient,
    account_id: Any,
    conversation_id: Any,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """GET + PATCH para no pisar atributos de negocio ya existentes en la conversación."""
    prev = await _chatwoot_fetch_conversation(client, account_id, conversation_id)
    existing_raw = (prev or {}).get("custom_attributes")
    existing: dict[str, Any] = existing_raw if isinstance(existing_raw, dict) else {}
    merged = {**existing, **updates}
    url = (
        f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}"
        f"/conversations/{conversation_id}"
    )
    r = await client.patch(
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


async def _dify_blocking_reply(query: str, chatwoot_conversation_id: str) -> str:
    """POST /chat-messages en modo blocking. Documentación: Dify Chatflow / Advanced Chat API."""
    if not DIFY_API_KEY:
        raise RuntimeError("DIFY_API_KEY no configurada")
    url = f"{DIFY_API_BASE}/chat-messages"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "inputs": {},
        "query": query,
        "response_mode": "blocking",
        "user": f"chatwoot-{chatwoot_conversation_id}",
    }
    prev = _dify_conversation_by_chatwoot.get(chatwoot_conversation_id)
    if prev:
        body["conversation_id"] = prev

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=body, headers=headers)

    if response.status_code >= 300:
        raise RuntimeError(f"Dify HTTP {response.status_code}: {response.text[:500]}")

    data = response.json()
    new_cid = data.get("conversation_id")
    if isinstance(new_cid, str) and new_cid:
        _dify_conversation_by_chatwoot[chatwoot_conversation_id] = new_cid

    answer = data.get("answer")
    if isinstance(answer, str) and answer.strip():
        return answer.strip()

    raise RuntimeError(f"Respuesta Dify sin campo answer: {str(data)[:300]}")


def _dify_service_root() -> str:
    """Raíz HTTP del servicio API de Dify (GET /health vive fuera del prefijo /v1)."""
    base = DIFY_API_BASE.rstrip("/")
    if base.endswith("/v1"):
        return base[: -len("/v1")].rstrip("/") or base
    return base


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "bridge_build": BRIDGE_BUILD,
        "endpoints": ["/health", "/health/dify", "/webhooks/chatwoot"],
    }


@app.get("/health/dify")
async def health_dify() -> dict[str, Any]:
    """Comprueba red hasta el contenedor `api` de Dify (no usa la app API key)."""
    root = _dify_service_root()
    url = f"{root}/health"
    out: dict[str, Any] = {
        "dify_service_url": root,
        "ping_url": url,
        "app_key_configured": bool(DIFY_API_KEY),
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url)
        out["http_status"] = r.status_code
        out["reachable"] = r.status_code < 500
        try:
            out["dify_health"] = r.json()
        except json.JSONDecodeError:
            out["dify_health_preview"] = r.text[:200]
    except httpx.RequestError as exc:
        out["reachable"] = False
        out["error"] = str(exc)[:400]
    return out


@app.post("/webhooks/chatwoot")
async def chatwoot_webhook(request: Request) -> dict[str, Any]:
    raw_body = await request.body()
    _verify_chatwoot_webhook_signature(raw_body, request)
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido") from None
    event = payload.get("event")

    if event != "message_created":
        return {"ok": True, "ignored": True, "reason": "non_message_created_event"}

    if not _is_incoming_user_message(payload):
        return {"ok": True, "ignored": True, "reason": "not_incoming_user_message"}

    account_id = _safe_get(payload, "account", "id")
    conversation_id = _safe_get(payload, "conversation", "id")

    if not account_id or not conversation_id:
        raise HTTPException(
            status_code=400,
            detail="Webhook sin account_id o conversation_id",
        )

    if not CHATWOOT_API_TOKEN:
        return {
            "ok": True,
            "ignored": True,
            "reason": "missing_chatwoot_api_token",
        }

    cw_cid = str(conversation_id)
    user_text = _chatwoot_message_text(payload)
    if not user_text:
        return {"ok": True, "ignored": True, "reason": "empty_message_content"}

    if DIFY_API_KEY:
        try:
            reply_text = await _dify_blocking_reply(user_text, cw_cid)
            source = "dify"
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Error llamando a Dify: {exc}",
            ) from exc
    else:
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
    lead: dict[str, Any] | None = None
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        response = await client.post(msg_url, json=msg_body, headers=headers)

        if response.status_code >= 300:
            raise HTTPException(
                status_code=502,
                detail=f"Error al publicar mensaje en Chatwoot: {response.text}",
            )

        if BRIDGE_SYNC_CHATWOOT_ATTRIBUTES:
            lead = _heuristic_lead_signals(user_text, ai_source=source)
            summary = reply_text.strip().replace("\n", " ")
            if len(summary) > 280:
                summary = summary[:277] + "..."
            updates: dict[str, Any] = {
                "lead_score": lead["lead_score"],
                "lead_temperature": lead["lead_temperature"],
                "handoff_recommended": lead["handoff_recommended"],
                "last_ai_summary": summary,
                "ai_source": source,
                "miwayki_bridge_build": BRIDGE_BUILD,
            }
            attr_report = await _chatwoot_merge_custom_attributes(
                client,
                account_id,
                conversation_id,
                updates,
            )

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
    return out
