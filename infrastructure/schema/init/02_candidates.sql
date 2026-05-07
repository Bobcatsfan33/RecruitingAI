-- Candidates: identity, career, comp, sales-motion, SE depth, clearance,
-- engagement signals, ownership/compliance, embedding, metadata.
-- Mirrors the candidate schema in PLATFORM-BLUEPRINT.md.

CREATE TYPE candidate_source AS ENUM (
    'linkedin', 'clearancejobs', 'referral', 'inbound', 'manual'
);

CREATE TYPE candidate_status AS ENUM (
    'active', 'passive', 'do_not_contact', 'placed', 'benched'
);

CREATE TYPE citizenship_status AS ENUM (
    'us_citizen', 'permanent_resident', 'visa_h1b', 'visa_other', 'unknown'
);

CREATE TYPE clearance_type AS ENUM (
    'none', 'public_trust', 'secret', 'top_secret', 'ts_sci'
);

CREATE TYPE polygraph_type AS ENUM (
    'none', 'ci', 'full_scope', 'lifestyle'
);

CREATE TYPE clearance_status AS ENUM (
    'active', 'interim', 'expired', 'in_process'
);

CREATE TYPE career_arc AS ENUM (
    'ascending', 'lateral', 'declining', 'pivoting'
);

CREATE TYPE sales_motion AS ENUM (
    'enterprise', 'mid_market', 'smb_velocity', 'plg', 'channel'
);

CREATE TYPE se_orientation AS ENUM ('pre_sales', 'post_sales', 'hybrid');

CREATE TYPE preferred_channel AS ENUM ('email', 'linkedin', 'phone', 'text');

CREATE TYPE availability_window AS ENUM (
    'immediately', 'two_weeks', 'thirty_days', 'not_looking'
);

CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source candidate_source NOT NULL,
    status candidate_status NOT NULL DEFAULT 'active',

    -- IDENTITY
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email CITEXT,
    phone TEXT,
    linkedin_url TEXT,
    location_city TEXT,
    location_state TEXT,
    location_metro TEXT,
    willing_to_relocate BOOLEAN NOT NULL DEFAULT FALSE,
    citizenship citizenship_status NOT NULL DEFAULT 'unknown',

    -- CAREER TRAJECTORY (jsonb array of role records)
    career_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    career_arc_classification career_arc,

    -- COMPENSATION ARCHAEOLOGY (jsonb array, one per role w/ verification flag)
    compensation_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    comp_trajectory TEXT, -- growing | flat | declining

    -- SALES MOTION
    primary_motion sales_motion,
    secondary_motion sales_motion,
    deal_cycle_min_days INT,
    deal_cycle_max_days INT,
    deal_cycle_avg_days INT,
    avg_acv NUMERIC(12,2),
    max_acv NUMERIC(12,2),
    methodology_experience TEXT[],

    -- SE TECHNICAL DEPTH (jsonb)
    se_domains JSONB NOT NULL DEFAULT '[]'::jsonb,
    se_vendor_specific JSONB NOT NULL DEFAULT '[]'::jsonb,
    se_orientation se_orientation,
    se_demo_skill_rating SMALLINT, -- 1-5

    -- CLEARANCE & COMPLIANCE
    clearance_type clearance_type NOT NULL DEFAULT 'none',
    polygraph polygraph_type NOT NULL DEFAULT 'none',
    investigation_date DATE,
    adjudication_date DATE,
    clearance_status clearance_status,
    read_on_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    facility_clearance_affiliations JSONB NOT NULL DEFAULT '[]'::jsonb,
    itar_ear_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    sap_sar_access JSONB NOT NULL DEFAULT '[]'::jsonb,
    deployability_score SMALLINT, -- 0-100, computed

    -- ENGAGEMENT SIGNALS
    last_contact_date TIMESTAMPTZ,
    last_response_date TIMESTAMPTZ,
    preferred_channel preferred_channel,
    response_rate_email REAL,
    response_rate_linkedin REAL,
    response_rate_phone REAL,
    approachability_score SMALLINT, -- 0-100
    counteroffer_risk_score SMALLINT, -- 0-100
    availability_window availability_window,
    referral_connections UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],

    -- EMBEDDING (1536 = OpenAI ada-002 / text-embedding-3-small dims)
    profile_embedding vector(1536),

    -- METADATA
    data_freshness_score SMALLINT NOT NULL DEFAULT 100,
    last_enrichment_date TIMESTAMPTZ,
    profile_completeness_score SMALLINT NOT NULL DEFAULT 0,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],

    -- internal versioning
    schema_version SMALLINT NOT NULL DEFAULT 1,

    -- Engagement / outreach uniqueness
    CONSTRAINT candidates_email_or_phone_or_li
        CHECK (email IS NOT NULL OR phone IS NOT NULL OR linkedin_url IS NOT NULL)
);

-- Make email lookup case-insensitive (CITEXT) and unique when present.
CREATE EXTENSION IF NOT EXISTS citext;
CREATE UNIQUE INDEX candidates_email_uq ON candidates (email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX candidates_linkedin_uq ON candidates (linkedin_url) WHERE linkedin_url IS NOT NULL;

CREATE INDEX candidates_status_idx ON candidates (status);
CREATE INDEX candidates_clearance_idx ON candidates (clearance_type, polygraph);
CREATE INDEX candidates_location_idx ON candidates (location_metro, location_state);
CREATE INDEX candidates_motion_idx ON candidates (primary_motion);
CREATE INDEX candidates_updated_idx ON candidates (updated_at DESC);
CREATE INDEX candidates_tags_gin ON candidates USING gin (tags);
CREATE INDEX candidates_career_history_gin ON candidates USING gin (career_history);
-- IVFFlat works once we have ~1k vectors; HNSW is the upgrade path at >100k.
CREATE INDEX candidates_embedding_idx ON candidates
    USING ivfflat (profile_embedding vector_cosine_ops) WITH (lists = 100);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER candidates_set_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
