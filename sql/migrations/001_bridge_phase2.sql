-- ============================================================================
-- MiWayki Bridge — Fase 2: Motor Comercial
-- Migración: crear schema y tablas para leads, quotes, reservations, sessions.
-- Ejecutar en el PostgreSQL existente (miwayki-postgres).
-- ============================================================================
--
-- Uso:
--   docker exec -i miwayki-postgres psql -U miwayki_app -d miwayki < sql/migrations/001_bridge_phase2.sql
--
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS bridge;

-- ── Leads ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge.leads (
    id                       SERIAL PRIMARY KEY,
    chatwoot_conversation_id INTEGER NOT NULL UNIQUE,
    chatwoot_contact_id      INTEGER,
    commercial_state         VARCHAR(30) NOT NULL DEFAULT 'new_inquiry',
    lead_score               INTEGER NOT NULL DEFAULT 0,
    lead_temperature         VARCHAR(10) NOT NULL DEFAULT 'cold',
    customer_name            TEXT,
    customer_email           TEXT,
    customer_phone           TEXT,
    destination              TEXT,
    travel_dates             TEXT,
    party_size               INTEGER,
    group_type               VARCHAR(30) DEFAULT 'individual',
    budget_range             TEXT,
    urgency                  VARCHAR(20) DEFAULT 'low',
    special_requirements     TEXT,
    last_quote_id            INTEGER,
    handoff_required         BOOLEAN NOT NULL DEFAULT FALSE,
    handoff_reason           TEXT,
    seller_notes             TEXT,
    langflow_conversation_id TEXT,
    metadata                 JSONB NOT NULL DEFAULT '{}',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_leads_state ON bridge.leads(commercial_state);
CREATE INDEX IF NOT EXISTS idx_leads_conversation ON bridge.leads(chatwoot_conversation_id);

-- ── Quotes ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge.quotes (
    id                       SERIAL PRIMARY KEY,
    lead_id                  INTEGER NOT NULL REFERENCES bridge.leads(id),
    tour_code                TEXT NOT NULL,
    variant_code             TEXT,
    travel_date              DATE NOT NULL,
    party_size               INTEGER NOT NULL,
    group_type               VARCHAR(30) DEFAULT 'individual',
    base_price_per_person    NUMERIC(10,2) NOT NULL,
    base_total               NUMERIC(10,2) NOT NULL,
    season_name              TEXT,
    season_adjustment        NUMERIC(10,2) NOT NULL DEFAULT 0,
    holiday_name             TEXT,
    holiday_adjustment       NUMERIC(10,2) NOT NULL DEFAULT 0,
    group_adjustment         NUMERIC(10,2) NOT NULL DEFAULT 0,
    exception_adjustment     NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_price_pen          NUMERIC(10,2) NOT NULL,
    per_person_pen           NUMERIC(10,2) NOT NULL,
    price_breakdown          JSONB NOT NULL DEFAULT '{}',
    valid_until              TIMESTAMPTZ NOT NULL,
    status                   VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quotes_lead ON bridge.quotes(lead_id);

-- ── Reservations ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge.reservations (
    id                       SERIAL PRIMARY KEY,
    lead_id                  INTEGER NOT NULL REFERENCES bridge.leads(id),
    quote_id                 INTEGER NOT NULL REFERENCES bridge.quotes(id),
    status                   VARCHAR(30) NOT NULL DEFAULT 'pending',
    payment_amount           NUMERIC(10,2) NOT NULL,
    payment_currency         VARCHAR(5) NOT NULL DEFAULT 'PEN',
    bank_account_info        JSONB NOT NULL DEFAULT '{}',
    voucher_reference        TEXT,
    voucher_received_at      TIMESTAMPTZ,
    confirmed_at             TIMESTAMPTZ,
    confirmed_by             TEXT,
    notes                    TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reservations_lead ON bridge.reservations(lead_id);

-- ── Langflow Sessions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge.langflow_sessions (
    chatwoot_conversation_id INTEGER PRIMARY KEY,
    langflow_conversation_id TEXT NOT NULL,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
