-- AutoEdge MVP schema
-- Uitvoeren via pgAdmin (Query Tool) of psql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── LISTINGS ───────────────────────────────────────────────────────────────
-- Ruwe advertentiedata van alle bronnen (2dehands, autovlan, ...)

CREATE TABLE IF NOT EXISTS listings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source          VARCHAR(30)   NOT NULL,        -- '2dehands', 'autovlan'
    external_id     VARCHAR(100)  NOT NULL,
    merk            VARCHAR(50),
    model           VARCHAR(80),
    bouwjaar        SMALLINT,
    km              INTEGER,
    prijs           NUMERIC(10,2),
    brandstof       VARCHAR(20),
    transmissie     VARCHAR(15),
    regio           VARCHAR(50),
    beschrijving    TEXT,
    url             TEXT,
    foto_urls       TEXT[],
    online_sinds    TIMESTAMPTZ,
    gezien_op       TIMESTAMPTZ   DEFAULT NOW(),
    actief          BOOLEAN       DEFAULT TRUE,
    UNIQUE(source, external_id)
);

-- ─── SCORES ─────────────────────────────────────────────────────────────────
-- Deal-score en analyse per listing (berekend door scoring.py)

CREATE TABLE IF NOT EXISTS scores (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id           UUID REFERENCES listings(id) ON DELETE CASCADE,
    deal_score           SMALLINT,
    marktwaarde          NUMERIC(10,2),
    prijs_afwijking_pct  NUMERIC(5,2),
    winst_potentieel     NUMERIC(10,2),
    score_prijs          SMALLINT,
    score_km             SMALLINT,
    score_staat          SMALLINT,
    score_urgentie       SMALLINT,
    risico_vlaggen       TEXT[],
    berekend_op          TIMESTAMPTZ DEFAULT NOW()
);

-- ─── MARKTPRIJZEN ───────────────────────────────────────────────────────────
-- Nightly berekende marktwaarden per segment (lookup-tabel voor scoring)

CREATE TABLE IF NOT EXISTS marktprijzen (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merk_model      VARCHAR(130) NOT NULL,
    bouwjaar        SMALLINT     NOT NULL,
    km_klasse       VARCHAR(20)  NOT NULL,   -- '0-50k', '50-100k', '100-150k'
    mediaan_prijs   NUMERIC(10,2),
    p25_prijs       NUMERIC(10,2),
    p75_prijs       NUMERIC(10,2),
    aantal_samples  INTEGER,
    bijgewerkt_op   TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE(merk_model, bouwjaar, km_klasse)
);

-- ─── USERS ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email             VARCHAR(255) UNIQUE,
    telegram_chat_id  VARCHAR(50),
    profiel_type      VARCHAR(15)  DEFAULT 'particulier',  -- of 'flipper'
    aangemaakt_op     TIMESTAMPTZ  DEFAULT NOW()
);

-- ─── ALERTS ─────────────────────────────────────────────────────────────────
-- Zoekopdrachten van gebruikers met notificatiecriteria

CREATE TABLE IF NOT EXISTS alerts (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
    naam          VARCHAR(100),
    merk          VARCHAR(50),
    model         VARCHAR(80),
    bouwjaar_min  SMALLINT,
    bouwjaar_max  SMALLINT,
    prijs_max     NUMERIC(10,2),
    km_max        INTEGER,
    min_score     SMALLINT    DEFAULT 60,
    kanaal        VARCHAR(15) DEFAULT 'telegram',   -- 'telegram' of 'email'
    actief        BOOLEAN     DEFAULT TRUE,
    aangemaakt_op TIMESTAMPTZ DEFAULT NOW()
);

-- ─── ALERT MATCHES ──────────────────────────────────────────────────────────
-- Bijhouding welke listings al verstuurd zijn (voorkomt dubbele notificaties)

CREATE TABLE IF NOT EXISTS alert_matches (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id     UUID REFERENCES alerts(id)   ON DELETE CASCADE,
    listing_id   UUID REFERENCES listings(id) ON DELETE CASCADE,
    verstuurd_op TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(alert_id, listing_id)
);

-- ─── INDEXEN ────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_listings_merk_model
    ON listings(merk, model, bouwjaar, km);

CREATE INDEX IF NOT EXISTS idx_listings_actief
    ON listings(actief, gezien_op DESC);

CREATE INDEX IF NOT EXISTS idx_scores_listing
    ON scores(listing_id);

CREATE INDEX IF NOT EXISTS idx_scores_deal_score
    ON scores(deal_score DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_actief
    ON alerts(actief, user_id);
