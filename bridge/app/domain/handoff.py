from __future__ import annotations

"""Evaluador de reglas de handoff (fase2local §8).

Reglas evaluadas en orden de prioridad:
H1: Grupo grande (> HANDOFF_MAX_GROUP_SIZE)
H2: Grupo escolar (siempre handoff)
H3: Tour/ruta no encontrada
H4: Fecha demasiado lejana (> HANDOFF_MAX_FUTURE_MONTHS)
H5: Voucher recibido (siempre handoff — regla de negocio no negociable)
H6: Score alto (>= HANDOFF_SCORE_THRESHOLD)
"""

from datetime import date, timedelta

from app.config.settings import (
    HANDOFF_MAX_GROUP_SIZE,
    HANDOFF_MAX_FUTURE_MONTHS,
    HANDOFF_SCORE_THRESHOLD,
)


class HandoffResult:
    """Resultado de la evaluación de handoff."""
    def __init__(self, required: bool, reason: str = None):  # type: ignore[assignment]
        self.required = required
        self.reason = reason


def evaluate_handoff(
    *,
    party_size: int = None,  # type: ignore[assignment]
    group_type: str = None,  # type: ignore[assignment]
    travel_date: date = None,  # type: ignore[assignment]
    lead_score: int = 0,
    tour_found: bool = True,
    is_voucher: bool = False,
    failed_quotes: int = 0,
) -> HandoffResult:
    """Evalúa todas las condiciones de handoff y retorna la primera que aplique."""

    # H1: Grupo grande
    if party_size is not None and party_size > HANDOFF_MAX_GROUP_SIZE:
        return HandoffResult(
            True,
            f"Grupo de {party_size} personas excede el máximo ({HANDOFF_MAX_GROUP_SIZE})",
        )

    # H2: Grupo escolar
    if group_type == "school":
        return HandoffResult(True, "Grupo escolar requiere atención especial")

    # H3: Tour no encontrado
    if not tour_found:
        return HandoffResult(True, "Tour/ruta no encontrada en el catálogo")

    # H4: Fecha muy lejana
    if travel_date is not None:
        max_date = date.today() + timedelta(days=HANDOFF_MAX_FUTURE_MONTHS * 30)
        if travel_date > max_date:
            return HandoffResult(
                True,
                f"Fecha de viaje ({travel_date}) supera el rango operativo "
                f"({HANDOFF_MAX_FUTURE_MONTHS} meses)",
            )

    # H5: Voucher recibido (no negociable)
    if is_voucher:
        return HandoffResult(True, "Voucher recibido — requiere verificación humana")

    # H6: Score alto
    if lead_score >= HANDOFF_SCORE_THRESHOLD:
        return HandoffResult(
            True,
            f"Lead score ({lead_score}) ≥ umbral de handoff ({HANDOFF_SCORE_THRESHOLD})",
        )

    return HandoffResult(False)
