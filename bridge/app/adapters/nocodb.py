from __future__ import annotations

"""Adaptador NocoDB — catálogo comercial vivo (fase2local §3).

NocoDB v2 REST API:
- Auth: header xc-token
- Records: GET /api/v2/meta/tables/{tableId}/records
- Where clause: (field,op,value) con operadores eq, neq, gt, lt, gte, lte, like
- Conjunción: ~and, ~or
- Paginación: limit, offset
- Rate limit: ~5 req/s

Cache en memoria con TTL configurable para no saturar NocoDB con queries repetitivas.
"""

import time
from datetime import date
from typing import Any

import httpx

from app.config.settings import (
    NOCODB_BASE_URL,
    NOCODB_API_TOKEN,
    NOCODB_CACHE_TTL,
    NOCODB_TABLE_ID_TOURS,
    NOCODB_TABLE_ID_VARIANTS,
    NOCODB_TABLE_ID_SEASONS,
    NOCODB_TABLE_ID_HOLIDAYS,
    NOCODB_TABLE_ID_PRICING_RULES,
    NOCODB_TABLE_ID_BANK_ACCOUNTS,
    NOCODB_TABLE_ID_EXCEPTIONS,
)
from app.utils.logging import log


class CatalogUnavailableError(Exception):
    """NocoDB inalcanzable o error de autenticación."""
    pass


# ── Cache en memoria ─────────────────────────────────────────────────────

class _Cache:
    """Cache en memoria con TTL. Suficiente para volumen local."""

    def __init__(self, ttl: int):
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def invalidate(self, key: str | None = None) -> None:
        if key is None:
            self._store.clear()
        elif key in self._store:
            del self._store[key]


_cache = _Cache(NOCODB_CACHE_TTL)


# ── Core fetch ───────────────────────────────────────────────────────────

async def _fetch_records(table_id: str, *, where: str | None = None) -> list[dict]:
    """GET NocoDB v2 records de una tabla."""
    if not table_id:
        log.warning("nocodb_table_id_not_configured")
        return []

    cache_key = f"{table_id}:{where or 'all'}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
    params: dict[str, Any] = {"limit": 200}
    if where:
        params["where"] = where

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                params=params,
                headers={"xc-token": NOCODB_API_TOKEN},
            )
        if r.status_code == 401:
            raise CatalogUnavailableError("NocoDB auth error (401) — verificar NOCODB_API_TOKEN")
        if r.status_code >= 300:
            log.error(
                "nocodb_fetch_error: status=%d table=%s body=%s",
                r.status_code, table_id, r.text[:300],
            )
            return []
        data = r.json()
        records = data.get("list", []) if isinstance(data, dict) else []
        _cache.set(cache_key, records)
        return records
    except httpx.RequestError as exc:
        raise CatalogUnavailableError(f"NocoDB inalcanzable: {exc}") from exc


# ── Tours ────────────────────────────────────────────────────────────────

async def list_tours(*, active_only: bool = True) -> list[dict]:
    """Lista todos los tours del catálogo."""
    where = "(active,eq,true)" if active_only else None
    return await _fetch_records(NOCODB_TABLE_ID_TOURS, where=where)


async def get_tour(tour_code: str) -> dict | None:
    """Busca un tour por su código único."""
    records = await _fetch_records(
        NOCODB_TABLE_ID_TOURS, where=f"(code,eq,{tour_code})"
    )
    return records[0] if records else None


# ── Variantes ────────────────────────────────────────────────────────────

async def list_variants(tour_code: str, *, active_only: bool = True) -> list[dict]:
    """Lista las variantes de un tour."""
    w = f"(tour_code,eq,{tour_code})"
    if active_only:
        w += "~and(active,eq,true)"
    return await _fetch_records(NOCODB_TABLE_ID_VARIANTS, where=w)


async def get_variant(tour_code: str, variant_code: str) -> dict | None:
    """Obtiene una variante específica."""
    w = f"(tour_code,eq,{tour_code})~and(code,eq,{variant_code})"
    records = await _fetch_records(NOCODB_TABLE_ID_VARIANTS, where=w)
    return records[0] if records else None


# ── Temporadas ───────────────────────────────────────────────────────────

async def get_season_for_date(travel_date: date) -> dict | None:
    """Encuentra la temporada que aplica para una fecha de viaje."""
    ds = travel_date.isoformat()
    w = f"(start_date,lte,{ds})~and(end_date,gte,{ds})~and(active,eq,true)"
    records = await _fetch_records(NOCODB_TABLE_ID_SEASONS, where=w)
    return records[0] if records else None


# ── Feriados ─────────────────────────────────────────────────────────────

async def get_holiday_for_date(travel_date: date) -> dict | None:
    """Encuentra el feriado que aplica para una fecha de viaje."""
    ds = travel_date.isoformat()
    w = f"(start_date,lte,{ds})~and(end_date,gte,{ds})~and(active,eq,true)"
    records = await _fetch_records(NOCODB_TABLE_ID_HOLIDAYS, where=w)
    return records[0] if records else None


# ── Reglas de precios ────────────────────────────────────────────────────

async def list_pricing_rules(party_size: int, group_type: str) -> list[dict]:
    """Lista las reglas de precio aplicables a un grupo.
    Filtrado parcial en NocoDB (active) + filtrado fino en Python
    (group_type, min/max pax) porque NocoDB where no soporta OR/NULL fácilmente.
    """
    records = await _fetch_records(
        NOCODB_TABLE_ID_PRICING_RULES, where="(active,eq,true)"
    )
    applicable = []
    for r in records:
        r_gt = r.get("group_type", "any")
        if r_gt not in (group_type, "any", None, ""):
            continue
        r_min = r.get("min_pax")
        r_max = r.get("max_pax")
        if r_min is not None and party_size < int(r_min):
            continue
        if r_max is not None and party_size > int(r_max):
            continue
        applicable.append(r)
    return sorted(applicable, key=lambda x: x.get("priority", 999))


# ── Cuentas bancarias ───────────────────────────────────────────────────

async def list_bank_accounts(*, currency: str = "PEN") -> list[dict]:
    """Lista cuentas bancarias activas para depósitos."""
    w = f"(currency,eq,{currency})~and(active,eq,true)"
    return await _fetch_records(NOCODB_TABLE_ID_BANK_ACCOUNTS, where=w)


# ── Excepciones comerciales ─────────────────────────────────────────────

async def list_exceptions(tour_code: str | None, travel_date: date) -> list[dict]:
    """Lista excepciones comerciales aplicables (promos, overrides, etc.).
    Excepciones sin tour_code aplican a todos los tours.
    """
    ds = travel_date.isoformat()
    records = await _fetch_records(
        NOCODB_TABLE_ID_EXCEPTIONS, where="(active,eq,true)"
    )
    applicable = []
    for r in records:
        r_tour = r.get("tour_code")
        if r_tour and r_tour != tour_code:
            continue
        r_start = r.get("start_date")
        r_end = r.get("end_date")
        if r_start and ds < r_start:
            continue
        if r_end and ds > r_end:
            continue
        applicable.append(r)
    return applicable


# ── Health check ─────────────────────────────────────────────────────────

async def check_health() -> dict[str, Any]:
    """Verifica conectividad con NocoDB."""
    out: dict[str, Any] = {
        "nocodb_url": NOCODB_BASE_URL,
        "token_configured": bool(NOCODB_API_TOKEN),
        "tables_configured": bool(NOCODB_TABLE_ID_TOURS),
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{NOCODB_BASE_URL}/api/v1/health",
                headers={"xc-token": NOCODB_API_TOKEN},
            )
        out["http_status"] = r.status_code
        out["reachable"] = r.status_code < 500
    except httpx.RequestError as exc:
        out["reachable"] = False
        out["error"] = str(exc)[:300]
    return out
