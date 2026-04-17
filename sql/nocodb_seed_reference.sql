-- ============================================================================
-- NocoDB Seed Data — Datos semilla para el catálogo comercial MiWayki
-- ============================================================================
--
-- ESTOS DATOS SE CARGAN EN NocoDB VIA LA UI WEB (http://localhost:8090).
-- Este archivo es REFERENCIA para saber qué columnas crear en cada tabla.
--
-- Instrucciones:
-- 1. Acceder a NocoDB: http://localhost:8090
-- 2. Crear un nuevo "Base" (proyecto) llamado "miwayki_catalog"
-- 3. Crear las 7 tablas con las columnas indicadas abajo
-- 4. Insertar los datos de ejemplo
-- 5. Generar un API token: Settings → API Tokens → Add
-- 6. Copiar los Table IDs (aparecen en la URL al seleccionar cada tabla)
-- 7. Configurar en .env.bridge: NOCODB_API_TOKEN y NOCODB_TABLE_ID_*
--
-- ============================================================================

-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLA 1: tours                                                        │
-- │ Columnas: code, name, description, base_price_pen, duration_days,     │
-- │           min_pax, max_pax, includes, excludes, active                │
-- └─────────────────────────────────────────────────────────────────────────┘
-- code (SingleLineText, Primary Key)
-- name (SingleLineText)
-- description (LongText)
-- base_price_pen (Number, decimal)
-- duration_days (Number, integer)
-- min_pax (Number, integer, default 1)
-- max_pax (Number, integer, default 30)
-- includes (LongText)
-- excludes (LongText)
-- active (Checkbox, default true)

-- Datos semilla:
-- | code             | name                        | base_price_pen | duration_days | min_pax | max_pax |
-- |------------------|-----------------------------|----------------|---------------|---------|---------|
-- | cusco-clasico    | Cusco Clásico               | 450.00         | 4             | 1       | 20      |
-- | valle-sagrado    | Valle Sagrado               | 380.00         | 1             | 2       | 30      |
-- | machu-picchu-1d  | Machu Picchu Full Day       | 650.00         | 1             | 1       | 15      |
-- | rainbow-mountain | Montaña de 7 Colores        | 250.00         | 1             | 2       | 20      |
-- | cusco-aventura   | Cusco Aventura (4D/3N)      | 980.00         | 4             | 2       | 12      |


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLA 2: tour_variants                                                │
-- │ Columnas: code, tour_code, name, description, price_adjustment_pen,   │
-- │           duration_days, active                                        │
-- └─────────────────────────────────────────────────────────────────────────┘
-- code (SingleLineText, Primary Key)
-- tour_code (SingleLineText, FK lógico → tours.code)
-- name (SingleLineText)
-- description (LongText, optional)
-- price_adjustment_pen (Number, decimal — puede ser negativo)
-- duration_days (Number, integer, optional — override del tour)
-- active (Checkbox, default true)

-- Datos semilla:
-- | code                    | tour_code     | name           | price_adjustment_pen |
-- |-------------------------|---------------|----------------|---------------------|
-- | cusco-clasico-premium   | cusco-clasico | Premium        | 120.00              |
-- | cusco-clasico-budget    | cusco-clasico | Económico      | -80.00              |
-- | machu-picchu-1d-tren-vip| machu-picchu-1d| Tren VIP      | 200.00              |
-- | cusco-aventura-vip      | cusco-aventura| VIP All Incl.  | 350.00              |


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLA 3: seasons                                                      │
-- │ Columnas: name, start_date, end_date, multiplier, active              │
-- └─────────────────────────────────────────────────────────────────────────┘
-- name (SingleLineText)
-- start_date (Date — YYYY-MM-DD)
-- end_date (Date — YYYY-MM-DD)
-- multiplier (Number, decimal — 1.0 = sin cambio, 1.25 = +25%)
-- active (Checkbox, default true)

-- Datos semilla:
-- | name           | start_date  | end_date    | multiplier |
-- |----------------|-------------|-------------|------------|
-- | Alta (Jun-Sep) | 2026-06-01  | 2026-09-30  | 1.25       |
-- | Media (Abr-May)| 2026-04-01  | 2026-05-31  | 1.10       |
-- | Media (Oct-Nov)| 2026-10-01  | 2026-11-30  | 1.10       |
-- | Baja (Dic-Mar) | 2025-12-01  | 2026-03-31  | 0.90       |


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLA 4: holidays                                                     │
-- │ Columnas: name, start_date, end_date, surcharge_pct, surcharge_pen,   │
-- │           active                                                      │
-- └─────────────────────────────────────────────────────────────────────────┘
-- name (SingleLineText)
-- start_date (Date — YYYY-MM-DD)
-- end_date (Date — YYYY-MM-DD)
-- surcharge_pct (Number, decimal — porcentaje, ej: 15 = +15%)
-- surcharge_pen (Number, decimal — monto fijo, alternativa a pct)
-- active (Checkbox, default true)

-- Datos semilla:
-- | name                   | start_date  | end_date    | surcharge_pct |
-- |------------------------|-------------|-------------|---------------|
-- | Fiestas Patrias        | 2026-07-28  | 2026-07-29  | 15            |
-- | Inti Raymi             | 2026-06-24  | 2026-06-24  | 20            |
-- | Semana Santa           | 2026-03-29  | 2026-04-05  | 10            |
-- | Fiestas de Fin de Año  | 2026-12-24  | 2027-01-02  | 20            |


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLA 5: pricing_rules                                                │
-- │ Columnas: rule_type, description, group_type, min_pax, max_pax,       │
-- │           discount_pct, surcharge_pct, flat_adjustment_pen, priority,  │
-- │           active                                                      │
-- └─────────────────────────────────────────────────────────────────────────┘
-- rule_type (SingleLineText — nombre técnico de la regla)
-- description (SingleLineText — nombre amigable para humanos)
-- group_type (SingleLineText — "individual", "family", "school", "corporate", "any")
-- min_pax (Number, integer, nullable)
-- max_pax (Number, integer, nullable)
-- discount_pct (Number, decimal, nullable)
-- surcharge_pct (Number, decimal, nullable)
-- flat_adjustment_pen (Number, decimal, nullable)
-- priority (Number, integer — menor = se aplica primero)
-- active (Checkbox, default true)

-- Datos semilla:
-- | rule_type       | description            | group_type | min_pax | max_pax | discount_pct | priority |
-- |-----------------|------------------------|------------|---------|---------|-------------|----------|
-- | family_4plus    | Familia 4+ personas    | family     | 4       |         | 10          | 1        |
-- | group_6plus     | Grupo 6+ personas      | any        | 6       | 15      | 5           | 2        |
-- | premium_1       | Individual sin descuento| individual| 1       | 1       |             | 10       |
-- | corporate_10plus| Corporativo 10+        | corporate  | 10      |         | 15          | 1        |


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLA 6: bank_accounts                                                │
-- │ Columnas: bank_name, account_holder, account_number, cci,             │
-- │           account_type, currency, active                              │
-- └─────────────────────────────────────────────────────────────────────────┘
-- bank_name (SingleLineText)
-- account_holder (SingleLineText)
-- account_number (SingleLineText)
-- cci (SingleLineText, nullable — código interbancario)
-- account_type (SingleLineText — "ahorros", "corriente")
-- currency (SingleLineText — "PEN", "USD")
-- active (Checkbox, default true)

-- Datos semilla:
-- | bank_name | account_holder       | account_number       | cci                    | account_type | currency |
-- |-----------|---------------------|---------------------|------------------------|-------------|----------|
-- | BCP       | MiWayki Tours SAC   | 285-12345678-0-12   | 002-285-12345678012-01 | ahorros      | PEN      |
-- | Interbank | MiWayki Tours SAC   | 200-3001234567      | 003-200-3001234567-01  | corriente    | PEN      |
-- | BCP       | MiWayki Tours SAC   | 285-87654321-1-12   | 002-285-87654321112-01 | ahorros      | USD      |


-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ TABLA 7: commercial_exceptions                                        │
-- │ Columnas: description, tour_code, start_date, end_date,               │
-- │           discount_pct, flat_price_pen, active                         │
-- └─────────────────────────────────────────────────────────────────────────┘
-- description (SingleLineText)
-- tour_code (SingleLineText, nullable — si vacío, aplica a todos)
-- start_date (Date, nullable)
-- end_date (Date, nullable)
-- discount_pct (Number, decimal, nullable)
-- flat_price_pen (Number, decimal, nullable — override total por persona)
-- active (Checkbox, default true)

-- Datos semilla:
-- | description            | tour_code     | start_date  | end_date    | discount_pct | flat_price_pen |
-- |------------------------|---------------|-------------|-------------|-------------|---------------|
-- | Promo Lanzamiento 2026 | cusco-clasico | 2026-04-01  | 2026-05-31  | 20          |               |
-- | Tarifa Plana Rainbow   | rainbow-mountain|           |             |             | 199.00        |
