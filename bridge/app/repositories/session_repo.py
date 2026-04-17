from __future__ import annotations

"""Repositorio de sesiones Langflow — reemplaza el dict en memoria del monolito."""

from typing import Optional

from app.repositories.database import get_pool


async def get_langflow_conversation_id(chatwoot_conv_id: int) -> Optional[str]:
    """Obtiene el conversation_id de Langflow para una conversación Chatwoot."""
    pool = await get_pool()
    return await pool.fetchval(
        "SELECT langflow_conversation_id FROM bridge.langflow_sessions WHERE chatwoot_conversation_id = $1",
        chatwoot_conv_id,
    )


async def set_langflow_conversation_id(chatwoot_conv_id: int, langflow_conv_id: str) -> None:
    """Guarda o actualiza el conversation_id de Langflow (UPSERT)."""
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO bridge.langflow_sessions (chatwoot_conversation_id, langflow_conversation_id, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (chatwoot_conversation_id)
        DO UPDATE SET langflow_conversation_id = $2, updated_at = NOW()
        """,
        chatwoot_conv_id, langflow_conv_id,
    )
