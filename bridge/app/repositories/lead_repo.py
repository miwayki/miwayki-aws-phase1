from __future__ import annotations

"""Repositorio de leads en PostgreSQL (schema bridge)."""

from typing import Any, Dict, List, Optional

from app.repositories.database import get_pool


async def upsert_lead(conversation_id: int, **fields: Any) -> Dict[str, Any]:
    """Crea o actualiza un lead. Retorna {lead_id, is_new, commercial_state}."""
    pool = await get_pool()

    # Intentar encontrar existente
    row = await pool.fetchrow(
        "SELECT id, commercial_state FROM bridge.leads WHERE chatwoot_conversation_id = $1",
        conversation_id,
    )

    if row is None:
        # Crear nuevo
        insert_fields: Dict[str, Any] = {"chatwoot_conversation_id": conversation_id}
        insert_fields.update({k: v for k, v in fields.items() if v is not None})

        columns = ", ".join(insert_fields.keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(insert_fields)))
        values = list(insert_fields.values())

        lead_id = await pool.fetchval(
            f"INSERT INTO bridge.leads ({columns}) VALUES ({placeholders}) RETURNING id",
            *values,
        )
        return {"lead_id": lead_id, "is_new": True, "commercial_state": "new_inquiry"}
    else:
        # Actualizar campos no-nulos
        updates = {k: v for k, v in fields.items() if v is not None}
        if updates:
            set_parts = []
            values: List[Any] = []
            for i, (k, v) in enumerate(updates.items()):
                set_parts.append(f"{k} = ${i+2}")
                values.append(v)
            set_clause = ", ".join(set_parts)
            await pool.execute(
                f"UPDATE bridge.leads SET {set_clause}, updated_at = NOW() WHERE id = $1",
                row["id"], *values,
            )
        return {
            "lead_id": row["id"],
            "is_new": False,
            "commercial_state": row["commercial_state"],
        }


async def get_lead_by_conversation(conversation_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene un lead por conversation_id de Chatwoot."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM bridge.leads WHERE chatwoot_conversation_id = $1",
        conversation_id,
    )
    if row is None:
        return None
    return dict(row)


async def update_state(lead_id: int, new_state: str) -> None:
    """Actualiza el estado comercial de un lead."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE bridge.leads SET commercial_state = $1, updated_at = NOW() WHERE id = $2",
        new_state, lead_id,
    )


async def update_lead_fields(lead_id: int, **fields: Any) -> None:
    """Actualiza campos individuales de un lead."""
    pool = await get_pool()
    updates = {k: v for k, v in fields.items() if v is not None}
    if not updates:
        return
    set_parts = []
    values: List[Any] = []
    for i, (k, v) in enumerate(updates.items()):
        set_parts.append(f"{k} = ${i+2}")
        values.append(v)
    set_clause = ", ".join(set_parts)
    await pool.execute(
        f"UPDATE bridge.leads SET {set_clause}, updated_at = NOW() WHERE id = $1",
        lead_id, *values,
    )
