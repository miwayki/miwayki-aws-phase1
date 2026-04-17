"""Funciones de seguridad: verificación de firma de webhook y filtrado anti-loop."""

import hashlib
import hmac
import time

from fastapi import HTTPException, Request

from app.utils import safe_get


def verify_chatwoot_webhook_signature(
    raw_body: bytes, request: Request, secret: str
) -> None:
    """Valida X-Chatwoot-Signature según documentación oficial.
    Extraído de main.py L63-87 sin cambios funcionales.
    """
    if not secret:
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
            secret.encode("utf-8"),
            signed_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail="Firma de webhook inválida")


def is_incoming_user_message(payload: dict) -> bool:
    """Filtra mensajes para evitar loops: solo procesar mensajes entrantes de contacto.
    Extraído de main.py L51-60 sin cambios funcionales.
    """
    message_type = safe_get(payload, "message_type")
    sender_type = safe_get(payload, "sender", "type")
    if sender_type and str(sender_type).lower() in {"agent", "bot"}:
        return False
    if message_type and str(message_type).lower() in {"outgoing", "template"}:
        return False
    return True
