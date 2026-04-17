from __future__ import annotations

"""Repositorio de cotizaciones en PostgreSQL (schema bridge)."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.config.settings import QUOTE_VALIDITY_DAYS
from app.repositories.database import get_pool


async def create_quote(lead_id: int, breakdown: Any) -> int:
    """Inserta una cotización y retorna quote_id. breakdown es un QuoteBreakdown dataclass."""
    pool = await get_pool()
    valid_until = datetime.now(timezone.utc) + timedelta(days=QUOTE_VALIDITY_DAYS)

    return await pool.fetchval(
        """
        INSERT INTO bridge.quotes (
            lead_id, tour_code, variant_code, travel_date, party_size, group_type,
            base_price_per_person, base_total, season_name, season_adjustment,
            holiday_name, holiday_adjustment, group_adjustment, exception_adjustment,
            total_price_pen, per_person_pen, price_breakdown, valid_until
        ) VALUES (
            $1, $2, $3, $4, $5, $6,
            $7, $8, $9, $10,
            $11, $12, $13, $14,
            $15, $16, $17, $18
        ) RETURNING id
        """,
        lead_id,
        breakdown.tour_code,
        breakdown.variant_code,
        breakdown.travel_date,
        breakdown.party_size,
        breakdown.group_type,
        float(breakdown.base_price_per_person),
        float(breakdown.base_total),
        breakdown.season_name,
        float(breakdown.season_adjustment),
        breakdown.holiday_name,
        float(breakdown.holiday_adjustment),
        float(breakdown.group_adjustment),
        float(breakdown.exception_adjustment),
        float(breakdown.total_price_pen),
        float(breakdown.per_person_pen),
        json.dumps({
            "rules": breakdown.group_rules_applied,
            "exceptions": breakdown.exceptions_applied,
        }),
        valid_until,
    )


async def get_active_quote(quote_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene una cotización activa no expirada."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM bridge.quotes WHERE id = $1 AND status = 'active' AND valid_until > NOW()",
        quote_id,
    )
    return dict(row) if row else None
