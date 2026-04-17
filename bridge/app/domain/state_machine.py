from __future__ import annotations

"""Máquina de estados comerciales (Fase 2 — fase2local §5).

7 estados:
- new_inquiry: Lead acaba de entrar
- quoted: Se generó al menos una cotización
- awaiting_payment: Aceptó cotización, esperamos depósito
- voucher_received: Envió comprobante de pago
- closed_won: Venta cerrada con éxito
- closed_lost: Lead perdido
- handoff: Escalado a humano

Estados terminales: closed_won, closed_lost (no permiten transiciones de salida).
"""


class InvalidTransitionError(Exception):
    """Transición de estado comercial no permitida."""
    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(f"Transición inválida: {current} → {target}")


VALID_TRANSITIONS: dict = {
    "new_inquiry":      {"quoted", "handoff", "closed_lost"},
    "quoted":           {"quoted", "awaiting_payment", "handoff", "closed_lost"},
    "awaiting_payment": {"voucher_received", "handoff", "closed_lost"},
    "voucher_received": {"closed_won", "handoff", "closed_lost"},
    "handoff":          {"closed_won", "closed_lost"},
    "closed_won":       set(),
    "closed_lost":      set(),
}

ALL_STATES = set(VALID_TRANSITIONS.keys())


def validate_transition(current: str, target: str) -> None:
    """Lanza InvalidTransitionError si la transición no es válida."""
    if current not in ALL_STATES:
        raise InvalidTransitionError(current, target)
    if target not in VALID_TRANSITIONS[current]:
        raise InvalidTransitionError(current, target)


def can_transition(current: str, target: str) -> bool:
    """Retorna True si la transición es válida, False si no."""
    if current not in ALL_STATES:
        return False
    return target in VALID_TRANSITIONS[current]


def is_terminal(state: str) -> bool:
    """Retorna True si el estado es terminal (closed_won o closed_lost)."""
    return state in ALL_STATES and len(VALID_TRANSITIONS.get(state, set())) == 0
