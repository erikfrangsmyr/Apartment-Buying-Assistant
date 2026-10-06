-- Apartment Buying Assistant — schema v1 (SQLite)
-- Lists/flags are stored as JSON text. Booleans are INTEGER 0/1.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tips (
    id          INTEGER PRIMARY KEY,
    category    TEXT    NOT NULL CHECK (category IN
                    ('brf_finance', 'renovation', 'legal', 'viewing', 'cost', 'negotiation')),
    title       TEXT    NOT NULL UNIQUE,
    body        TEXT    NOT NULL,
    importance  INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
    source      TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_tips_category ON tips (category, importance DESC);

CREATE TABLE IF NOT EXISTS criteria (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL UNIQUE,
    kind      TEXT    NOT NULL CHECK (kind IN ('hard', 'soft')),
    field     TEXT    NOT NULL,
    operator  TEXT    NOT NULL CHECK (operator IN ('>=', '<=', '=', 'in')),
    value     TEXT    NOT NULL CHECK (json_valid(value)),
    weight    INTEGER NOT NULL DEFAULT 3 CHECK (weight BETWEEN 1 AND 5),
    notes     TEXT
);

CREATE TABLE IF NOT EXISTS neighborhoods (
    id                 INTEGER PRIMARY KEY,
    name               TEXT    NOT NULL,
    municipality       TEXT    NOT NULL,
    commute_minutes    INTEGER CHECK (commute_minutes >= 0),
    avg_price_per_sqm  INTEGER CHECK (avg_price_per_sqm >= 0),
    notes              TEXT,
    rating             INTEGER CHECK (rating BETWEEN 1 AND 5),
    UNIQUE (name, municipality)
);

CREATE TABLE IF NOT EXISTS associations (
    id                INTEGER PRIMARY KEY,
    name              TEXT    NOT NULL,
    org_number        TEXT    UNIQUE CHECK (org_number IS NULL OR org_number GLOB '[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]'),
    neighborhood_id   INTEGER REFERENCES neighborhoods (id) ON DELETE SET NULL,
    built_year        INTEGER CHECK (built_year BETWEEN 1600 AND 2100),
    num_apartments    INTEGER CHECK (num_apartments > 0),
    total_debt        INTEGER CHECK (total_debt >= 0),
    debt_per_sqm      INTEGER CHECK (debt_per_sqm >= 0),
    cash_balance      INTEGER,
    owns_land         INTEGER CHECK (owns_land IN (0, 1)),
    tomtratt_fee      INTEGER CHECK (tomtratt_fee >= 0),
    is_genuine        INTEGER CHECK (is_genuine IN (0, 1)),
    planned_works     TEXT,
    last_report_year  INTEGER CHECK (last_report_year BETWEEN 1900 AND 2100),
    notes             TEXT
);
CREATE INDEX IF NOT EXISTS idx_associations_neighborhood ON associations (neighborhood_id);

CREATE TABLE IF NOT EXISTS renovations (
    id              INTEGER PRIMARY KEY,
    association_id  INTEGER NOT NULL REFERENCES associations (id) ON DELETE CASCADE,
    kind            TEXT    NOT NULL CHECK (kind IN ('roof', 'facade', 'stambyte', 'windows', 'elevator', 'other')),
    year            INTEGER CHECK (year BETWEEN 1600 AND 2100),
    status          TEXT    NOT NULL CHECK (status IN ('done', 'planned')),
    cost_estimate   INTEGER CHECK (cost_estimate >= 0),
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_renovations_association ON renovations (association_id);

CREATE TABLE IF NOT EXISTS listings (
    id               INTEGER PRIMARY KEY,
    association_id   INTEGER REFERENCES associations (id) ON DELETE SET NULL,
    neighborhood_id  INTEGER REFERENCES neighborhoods (id) ON DELETE SET NULL,
    address          TEXT    NOT NULL,
    url              TEXT,
    price            INTEGER CHECK (price >= 0),
    rooms            REAL    CHECK (rooms > 0),
    area_sqm         REAL    CHECK (area_sqm > 0),
    monthly_fee      INTEGER CHECK (monthly_fee >= 0),
    floor            INTEGER,
    status           TEXT    NOT NULL DEFAULT 'watching' CHECK (status IN ('watching', 'viewed', 'bid', 'rejected')),
    notes            TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings (status);
CREATE INDEX IF NOT EXISTS idx_listings_association ON listings (association_id);
CREATE INDEX IF NOT EXISTS idx_listings_neighborhood ON listings (neighborhood_id);

CREATE TABLE IF NOT EXISTS evaluations (
    id              INTEGER PRIMARY KEY,
    listing_id      INTEGER NOT NULL REFERENCES listings (id) ON DELETE CASCADE,
    criteria_score  REAL    CHECK (criteria_score BETWEEN 0 AND 100),
    brf_score       REAL    CHECK (brf_score BETWEEN 0 AND 100),
    summary         TEXT,
    red_flags       TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(red_flags)),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_evaluations_listing ON evaluations (listing_id, created_at DESC);
