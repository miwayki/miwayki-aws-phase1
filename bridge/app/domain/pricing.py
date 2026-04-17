from __future__ import annotations

"""Motor de precios. El Bridge es el dueño exclusivo del pricing (GEMINI.md).

Algoritmo de 6 pasos:
1. Precio base (tour + variante)
2. Ajuste por temporada (multiplier)
3. Ajuste por feriado (surcharge_pct o surcharge_pen)
4. Ajuste por grupo / pricing rules
5. Excepciones comerciales (discount_pct o flat_price override)
6. Total (nunca negativo)
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Optional


@dataclass
class QuoteBreakdown:
    """Resultado completo de una cotización con desglose paso a paso."""
    tour_code: str
    tour_name: str
    variant_code: Optional[str]
    variant_name: Optional[str]
    travel_date: date
    party_size: int
    group_type: str
    base_price_per_person: Decimal
    base_total: Decimal
    season_name: Optional[str] = None
    season_adjustment: Decimal = Decimal("0")
    holiday_name: Optional[str] = None
    holiday_adjustment: Decimal = Decimal("0")
    group_adjustment: Decimal = Decimal("0")
    group_rules_applied: List[str] = field(default_factory=list)
    exception_adjustment: Decimal = Decimal("0")
    exceptions_applied: List[str] = field(default_factory=list)
    total_price_pen: Decimal = Decimal("0")
    per_person_pen: Decimal = Decimal("0")
    is_override: bool = False


def _dec(value: Any) -> Decimal:
    """Convierte un valor numérico a Decimal de forma segura."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _round2(d: Decimal) -> Decimal:
    """Redondea a 2 decimales."""
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_quote(
    tour: dict,
    variant: Optional[dict],
    travel_date: date,
    party_size: int,
    group_type: str,
    season: Optional[dict],
    holiday: Optional[dict],
    pricing_rules: list,
    exceptions: list,
) -> QuoteBreakdown:
    """Algoritmo de cotización en 6 pasos (Etapa 2 — fase2local §5.2)."""

    # ── PASO 1: Precio base ──────────────────────────────────────────────
    base_per_person = _dec(tour.get("base_price_pen", 0))
    if variant:
        base_per_person += _dec(variant.get("price_adjustment_pen", 0))
    base_total = base_per_person * party_size

    result = QuoteBreakdown(
        tour_code=tour.get("code", ""),
        tour_name=tour.get("name", ""),
        variant_code=variant.get("code") if variant else None,
        variant_name=variant.get("name") if variant else None,
        travel_date=travel_date,
        party_size=party_size,
        group_type=group_type,
        base_price_per_person=_round2(base_per_person),
        base_total=_round2(base_total),
    )

    # ── PASO 2: Ajuste por temporada ─────────────────────────────────────
    if season and season.get("active", True):
        multiplier = _dec(season.get("multiplier", 1.0))
        result.season_name = season.get("name")
        result.season_adjustment = _round2(base_total * (multiplier - Decimal("1")))

    # ── PASO 3: Ajuste por feriado ───────────────────────────────────────
    if holiday and holiday.get("active", True):
        result.holiday_name = holiday.get("name")
        pct = _dec(holiday.get("surcharge_pct", 0))
        flat = _dec(holiday.get("surcharge_pen", 0))
        if pct:
            result.holiday_adjustment = _round2(base_total * pct / Decimal("100"))
        elif flat:
            result.holiday_adjustment = _round2(flat)

    # ── PASO 4: Ajuste por grupo / pricing rules ─────────────────────────
    group_adj = Decimal("0")
    for rule in sorted(pricing_rules, key=lambda r: r.get("priority", 999)):
        rule_group = rule.get("group_type", "any")
        if rule_group not in (group_type, "any"):
            continue
        r_min = rule.get("min_pax")
        r_max = rule.get("max_pax")
        if r_min is not None and party_size < int(r_min):
            continue
        if r_max is not None and party_size > int(r_max):
            continue

        desc = rule.get("description", rule.get("rule_type", "regla"))
        if rule.get("discount_pct"):
            adj = base_total * _dec(rule["discount_pct"]) / Decimal("100")
            group_adj -= adj
            result.group_rules_applied.append(f"{desc}: -{rule['discount_pct']}%")
        if rule.get("surcharge_pct"):
            adj = base_total * _dec(rule["surcharge_pct"]) / Decimal("100")
            group_adj += adj
            result.group_rules_applied.append(f"{desc}: +{rule['surcharge_pct']}%")
        if rule.get("flat_adjustment_pen"):
            group_adj += _dec(rule["flat_adjustment_pen"])
            sign = "+" if float(rule["flat_adjustment_pen"]) >= 0 else ""
            result.group_rules_applied.append(
                f"{desc}: {sign}S/ {rule['flat_adjustment_pen']}"
            )
    result.group_adjustment = _round2(group_adj)

    # ── PASO 5: Excepciones comerciales ──────────────────────────────────
    exc_adj = Decimal("0")
    for exc in exceptions:
        if not exc.get("active", True):
            continue
        desc = exc.get("description", "excepción")

        # Override: precio fijo reemplaza todo el cálculo
        flat_price = exc.get("flat_price_pen")
        if flat_price is not None and flat_price:
            override_total = _dec(flat_price) * party_size
            result.is_override = True
            result.exceptions_applied.append(f"{desc}: precio fijo S/ {flat_price}/pax")
            result.exception_adjustment = Decimal("0")
            result.total_price_pen = _round2(override_total)
            result.per_person_pen = _round2(_dec(flat_price))
            return result

        if exc.get("discount_pct"):
            adj = base_total * _dec(exc["discount_pct"]) / Decimal("100")
            exc_adj -= adj
            result.exceptions_applied.append(f"{desc}: -{exc['discount_pct']}%")
    result.exception_adjustment = _round2(exc_adj)

    # ── PASO 6: Total ────────────────────────────────────────────────────
    total = (
        base_total
        + result.season_adjustment
        + result.holiday_adjustment
        + result.group_adjustment
        + result.exception_adjustment
    )
    total = max(total, Decimal("0"))
    result.total_price_pen = _round2(total)
    result.per_person_pen = _round2(total / party_size) if party_size > 0 else Decimal("0")

    return result
