"""Configuración centralizada del Bridge. Todas las env vars en un solo lugar."""

import os
from typing import Any


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw == "":
        return default
    return raw in ("1", "true", "yes", "on", "y")


# ── Build ────────────────────────────────────────────────────────────────
BRIDGE_BUILD = "2.0-phase2-commercial"

# ── Chatwoot ─────────────────────────────────────────────────────────────
CHATWOOT_BASE_URL: str = os.getenv("CHATWOOT_BASE_URL", "http://chatwoot:3000")
CHATWOOT_API_TOKEN: str = os.getenv("CHATWOOT_API_TOKEN", "")
CHATWOOT_WEBHOOK_SECRET: str = os.getenv("CHATWOOT_WEBHOOK_SECRET", "").strip()
BRIDGE_AUTO_REPLY: str = os.getenv(
    "BRIDGE_AUTO_REPLY",
    "Recibido. Este es el bridge MVP de prueba conectado correctamente.",
)

# ── Langflow ─────────────────────────────────────────────────────────────────
LANGFLOW_API_BASE: str = os.getenv("LANGFLOW_API_BASE", "http://langflow:7860/api/v1").rstrip("/")
LANGFLOW_FLOW_ID: str = os.getenv("LANGFLOW_FLOW_ID", "").strip()
LANGFLOW_API_KEY: str = os.getenv("LANGFLOW_API_KEY", "").strip()

# ── Sync ─────────────────────────────────────────────────────────────────
BRIDGE_SYNC_CHATWOOT_ATTRIBUTES: bool = _env_bool("BRIDGE_SYNC_CHATWOOT_ATTRIBUTES", False)

# ── NocoDB ───────────────────────────────────────────────────────────────
NOCODB_BASE_URL: str = os.getenv("NOCODB_BASE_URL", "http://nocodb:8080")
NOCODB_API_TOKEN: str = os.getenv("NOCODB_API_TOKEN", "")
NOCODB_TABLE_ID_TOURS: str = os.getenv("NOCODB_TABLE_ID_TOURS", "")
NOCODB_TABLE_ID_VARIANTS: str = os.getenv("NOCODB_TABLE_ID_VARIANTS", "")
NOCODB_TABLE_ID_SEASONS: str = os.getenv("NOCODB_TABLE_ID_SEASONS", "")
NOCODB_TABLE_ID_HOLIDAYS: str = os.getenv("NOCODB_TABLE_ID_HOLIDAYS", "")
NOCODB_TABLE_ID_PRICING_RULES: str = os.getenv("NOCODB_TABLE_ID_PRICING_RULES", "")
NOCODB_TABLE_ID_BANK_ACCOUNTS: str = os.getenv("NOCODB_TABLE_ID_BANK_ACCOUNTS", "")
NOCODB_TABLE_ID_EXCEPTIONS: str = os.getenv("NOCODB_TABLE_ID_EXCEPTIONS", "")
NOCODB_CACHE_TTL: int = int(os.getenv("NOCODB_CACHE_TTL", "60"))

# ── PostgreSQL (Bridge persistence) ─────────────────────────────────────
BRIDGE_DATABASE_URL: str = os.getenv(
    "BRIDGE_DATABASE_URL",
    "postgresql://miwayki_app:change_me@postgres:5432/miwayki",
)

# ── Handoff thresholds ───────────────────────────────────────────────────
HANDOFF_MAX_GROUP_SIZE: int = int(os.getenv("HANDOFF_MAX_GROUP_SIZE", "15"))
HANDOFF_MAX_FUTURE_MONTHS: int = int(os.getenv("HANDOFF_MAX_FUTURE_MONTHS", "18"))
HANDOFF_SCORE_THRESHOLD: int = int(os.getenv("HANDOFF_SCORE_THRESHOLD", "70"))
HANDOFF_MAX_FAILED_QUOTES: int = int(os.getenv("HANDOFF_MAX_FAILED_QUOTES", "3"))

# ── Quote validity ───────────────────────────────────────────────────────
QUOTE_VALIDITY_DAYS: int = int(os.getenv("QUOTE_VALIDITY_DAYS", "7"))
