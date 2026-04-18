-- Script autogenerado de estabilización: Convierte el modelo de referencia en SQL ejecutable
CREATE SCHEMA IF NOT EXISTS catalog;
SET search_path TO catalog;

CREATE TABLE tours (
    code VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_price_pen NUMERIC(10,2) NOT NULL,
    duration_days INTEGER NOT NULL,
    min_pax INTEGER DEFAULT 1,
    max_pax INTEGER DEFAULT 30,
    includes TEXT,
    excludes TEXT,
    active BOOLEAN DEFAULT true
);

INSERT INTO tours (code, name, description, base_price_pen, duration_days, min_pax, max_pax) VALUES
('cusco-clasico', 'Cusco Clásico', 'Tour clásico por la ciudad.', 450.00, 4, 1, 20),
('valle-sagrado', 'Valle Sagrado', 'Recorrido por el Valle Sagrado de los Incas.', 380.00, 1, 2, 30),
('machu-picchu-1d', 'Machu Picchu Full Day', 'Visita en un día a la maravilla del mundo.', 650.00, 1, 1, 15),
('rainbow-mountain', 'Montaña de 7 Colores', 'Trekking a Vinicunca.', 250.00, 1, 2, 20),
('cusco-aventura', 'Cusco Aventura (4D/3N)', 'Tour activo e intenso por Cusco.', 980.00, 4, 2, 12);

CREATE TABLE tour_variants (
    code VARCHAR(50) PRIMARY KEY,
    tour_code VARCHAR(50) REFERENCES tours(code),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price_adjustment_pen NUMERIC(10,2) NOT NULL,
    duration_days INTEGER,
    active BOOLEAN DEFAULT true
);

INSERT INTO tour_variants (code, tour_code, name, price_adjustment_pen) VALUES
('cusco-clasico-premium', 'cusco-clasico', 'Premium', 120.00),
('cusco-clasico-budget', 'cusco-clasico', 'Económico', -80.00),
('machu-picchu-1d-tren-vip', 'machu-picchu-1d', 'Tren VIP', 200.00),
('cusco-aventura-vip', 'cusco-aventura', 'VIP All Incl.', 350.00);

CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    multiplier NUMERIC(5,2) NOT NULL,
    active BOOLEAN DEFAULT true
);

INSERT INTO seasons (name, start_date, end_date, multiplier) VALUES
('Alta (Jun-Sep)', '2026-06-01', '2026-09-30', 1.25),
('Media (Abr-May)', '2026-04-01', '2026-05-31', 1.10),
('Media (Oct-Nov)', '2026-10-01', '2026-11-30', 1.10),
('Baja (Dic-Mar)', '2025-12-01', '2026-03-31', 0.90);

CREATE TABLE holidays (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    surcharge_pct NUMERIC(5,2),
    surcharge_pen NUMERIC(10,2),
    active BOOLEAN DEFAULT true
);

INSERT INTO holidays (name, start_date, end_date, surcharge_pct) VALUES
('Fiestas Patrias', '2026-07-28', '2026-07-29', 15.00),
('Inti Raymi', '2026-06-24', '2026-06-24', 20.00),
('Semana Santa', '2026-03-29', '2026-04-05', 10.00),
('Fiestas de Fin de Año', '2026-12-24', '2027-01-02', 20.00);

CREATE TABLE pricing_rules (
    rule_type VARCHAR(50) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    group_type VARCHAR(50) NOT NULL,
    min_pax INTEGER,
    max_pax INTEGER,
    discount_pct NUMERIC(5,2),
    surcharge_pct NUMERIC(5,2),
    flat_adjustment_pen NUMERIC(10,2),
    priority INTEGER NOT NULL,
    active BOOLEAN DEFAULT true
);

INSERT INTO pricing_rules (rule_type, description, group_type, min_pax, max_pax, discount_pct, priority) VALUES
('family_4plus', 'Familia 4+ personas', 'family', 4, NULL, 10.00, 1),
('group_6plus', 'Grupo 6+ personas', 'any', 6, 15, 5.00, 2),
('premium_1', 'Individual sin descuento', 'individual', 1, 1, NULL, 10),
('corporate_10plus', 'Corporativo 10+', 'corporate', 10, NULL, 15.00, 1);

CREATE TABLE bank_accounts (
    id SERIAL PRIMARY KEY,
    bank_name VARCHAR(100) NOT NULL,
    account_holder VARCHAR(255) NOT NULL,
    account_number VARCHAR(100) NOT NULL,
    cci VARCHAR(100),
    account_type VARCHAR(50) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    active BOOLEAN DEFAULT true
);

INSERT INTO bank_accounts (bank_name, account_holder, account_number, cci, account_type, currency) VALUES
('BCP', 'MiWayki Tours SAC', '285-12345678-0-12', '002-285-12345678012-01', 'ahorros', 'PEN'),
('Interbank', 'MiWayki Tours SAC', '200-3001234567', '003-200-3001234567-01', 'corriente', 'PEN'),
('BCP', 'MiWayki Tours SAC', '285-87654321-1-12', '002-285-87654321112-01', 'ahorros', 'USD');

CREATE TABLE commercial_exceptions (
    id SERIAL PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    tour_code VARCHAR(50) REFERENCES tours(code),
    start_date DATE,
    end_date DATE,
    discount_pct NUMERIC(5,2),
    flat_price_pen NUMERIC(10,2),
    active BOOLEAN DEFAULT true
);

INSERT INTO commercial_exceptions (description, tour_code, start_date, end_date, discount_pct, flat_price_pen) VALUES
('Promo Lanzamiento 2026', 'cusco-clasico', '2026-04-01', '2026-05-31', 20.00, NULL),
('Tarifa Plana Rainbow', 'rainbow-mountain', NULL, NULL, NULL, 199.00);
