"""Motor de scoring heurístico. Extraído de main.py L99-149 sin cambios funcionales."""

from typing import Any


HOT_KEYWORDS = (
    "precio", "reserva", "pago", "teléfono", "telefono", "whatsapp",
    "correo", "email", "@", "fecha", "disponib", "cierre", "contacto",
    "llamada", "llámame", "reservar", "comprar", "tarjeta",
)

WARM_KEYWORDS = (
    "cuándo", "cuando", "dónde", "donde", "opciones", "paquete",
    "tour", "viaje", "presupuesto", "interesado", "información", "informacion",
)


def heuristic_lead_signals(user_text: str, *, ai_source: str) -> dict[str, Any]:
    """MVP alineado a master spec §13 (umbrales 0-39/40-69/70-100).
    Extraído de main.py L99-149 sin cambios funcionales.
    """
    t = user_text.lower()
    score, temp, handoff = 25, "cold", False

    if any(k in t for k in HOT_KEYWORDS):
        score, temp, handoff = 78, "hot", True
    elif len(t) > 100 or any(k in t for k in WARM_KEYWORDS):
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
