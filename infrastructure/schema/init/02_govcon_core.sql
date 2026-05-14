-- GovCon contract graph — agencies, vendors, contracts.

CREATE TABLE IF NOT EXISTS agencies (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name         TEXT NOT NULL,
    code         TEXT UNIQUE NOT NULL,
    department   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS agencies_name_trgm ON agencies USING gin (name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS vendors (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    uei             TEXT UNIQUE,
    duns            TEXT,
    cage_code       TEXT,
    size_standard   TEXT,
    set_aside_type  TEXT CHECK (set_aside_type IN ('none','8a','SDVOSB','HUBZONE','WOSB')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS vendors_name_trgm ON vendors USING gin (name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS contracts (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    piid              TEXT NOT NULL UNIQUE,
    title             TEXT NOT NULL,
    description       TEXT,
    naics_code        TEXT,
    contract_vehicle  TEXT,
    agency_id         UUID REFERENCES agencies(id) ON DELETE SET NULL,
    vendor_id         UUID REFERENCES vendors(id) ON DELETE SET NULL,
    pop_start         DATE,
    pop_end           DATE,
    current_value     NUMERIC(18, 2),
    potential_value   NUMERIC(18, 2),
    option_year       INTEGER,
    base_or_option    TEXT NOT NULL DEFAULT 'base' CHECK (base_or_option IN ('base','option')),
    is_incumbent      BOOLEAN NOT NULL DEFAULT FALSE,
    recompete_risk    TEXT CHECK (recompete_risk IN ('CRITICAL','HIGH','WATCH','STABLE')),
    status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','expired','cancelled')),
    source            TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('sam','fpds','usaspending','manual')),
    raw_json          JSONB,
    embedding         vector(1536),
    last_synced_at    TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS contracts_pop_end ON contracts (pop_end);
CREATE INDEX IF NOT EXISTS contracts_vendor ON contracts (vendor_id);
CREATE INDEX IF NOT EXISTS contracts_agency ON contracts (agency_id);
CREATE INDEX IF NOT EXISTS contracts_naics ON contracts (naics_code);
CREATE INDEX IF NOT EXISTS contracts_status_risk ON contracts (status, recompete_risk);
CREATE INDEX IF NOT EXISTS contracts_title_trgm ON contracts USING gin (title gin_trgm_ops);
-- pgvector ANN index — IVFFlat is appropriate for ≤1M rows; HNSW would be faster
-- once we cross that threshold but is more memory-hungry.
CREATE INDEX IF NOT EXISTS contracts_embedding_ivf
    ON contracts USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
