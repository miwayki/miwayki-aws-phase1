from __future__ import annotations

"""Pool de conexiones asyncpg para el Bridge."""

import asyncpg

from app.config.settings import BRIDGE_DATABASE_URL
from app.utils.logging import log

_pool: asyncpg.Pool = None  # type: ignore[assignment]


async def get_pool() -> asyncpg.Pool:
    """Obtiene o crea el pool de conexiones. Lazy initialization."""
    global _pool
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                BRIDGE_DATABASE_URL, min_size=2, max_size=10,
            )
            # Solo loggear la parte host:port/db del URL (sin password)
            safe_url = BRIDGE_DATABASE_URL.split("@")[-1] if "@" in BRIDGE_DATABASE_URL else "***"
            log.info("database_pool_created: %s", safe_url)
        except Exception as exc:
            log.critical("database_pool_failed: %s", str(exc))
            raise
    return _pool


async def close_pool() -> None:
    """Cierra el pool de conexiones. Llamar en shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None  # type: ignore[assignment]
        log.info("database_pool_closed")
