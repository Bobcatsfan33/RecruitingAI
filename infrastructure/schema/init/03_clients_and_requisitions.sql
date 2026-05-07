-- Clients (the buying side) and requisitions.

CREATE TYPE req_type AS ENUM (
    'precision', 'velocity', 'pre_award', 'contingent', 'direct_hire'
);

CREATE TYPE req_status AS ENUM (
    'intake', 'active', 'on_hold', 'filled', 'cancelled'
);

CREATE TYPE req_urgency AS ENUM (
    'critical_48h', 'standard_2wk', 'pipeline_30d', 'pre_award_speculative'
);

CREATE TYPE req_conviction_tier AS ENUM ('strong', 'moderate', 'weak');

CREATE TYPE req_exclusivity AS ENUM ('exclusive', 'non_exclusive', 'preferred');

CREATE TYPE comp_type AS ENUM ('salary', 'hourly', 'contract');

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    industry TEXT,
    is_federal BOOLEAN NOT NULL DEFAULT FALSE,
    contract_vehicles TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    -- Subscription tier governs access to advisory + intelligence features.
    subscription_tier TEXT NOT NULL DEFAULT 'free',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER clients_set_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE requisitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status req_status NOT NULL DEFAULT 'intake',

    -- CLASSIFICATION
    req_type req_type NOT NULL,
    urgency req_urgency NOT NULL DEFAULT 'standard_2wk',
    conviction_tier req_conviction_tier NOT NULL DEFAULT 'moderate',
    exclusivity req_exclusivity NOT NULL DEFAULT 'non_exclusive',

    -- ROLE REQUIREMENTS
    title TEXT NOT NULL,
    level TEXT,
    department TEXT,
    location_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    must_have_skills TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    nice_to_have_skills TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    years_experience_min SMALLINT,
    years_experience_max SMALLINT,
    education_requirement TEXT,
    role_specific_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- SALES-SPECIFIC
    motion_type_required sales_motion,
    quota_range_min NUMERIC(12,2),
    quota_range_max NUMERIC(12,2),
    vertical_experience_required TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    stack_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    company_tier_preference TEXT,

    -- CLEARANCE
    clearance_minimum clearance_type NOT NULL DEFAULT 'none',
    polygraph_required polygraph_type NOT NULL DEFAULT 'none',
    contract_vehicle TEXT,
    lcat_code TEXT,
    lcat_definition JSONB,
    period_of_performance_start DATE,
    period_of_performance_end DATE,
    facility_clearance_required BOOLEAN NOT NULL DEFAULT FALSE,

    -- COMPENSATION
    comp_type comp_type NOT NULL,
    budget_min NUMERIC(12,2),
    budget_max NUMERIC(12,2),
    pay_rate_min NUMERIC(12,2),
    pay_rate_max NUMERIC(12,2),
    target_margin_pct NUMERIC(5,4),
    conversion_fee_pct NUMERIC(5,4),
    market_alignment_score SMALLINT, -- computed by rules engine

    -- PIPELINE METRICS
    target_submissions INT NOT NULL DEFAULT 5,
    parallel_candidates_required INT NOT NULL DEFAULT 3,
    sla_days_to_first_submission INT,
    sla_days_to_fill INT,
    current_stage_counts JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- COMPETITIVE CONTEXT
    other_agencies_known TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    competitive_pressure TEXT NOT NULL DEFAULT 'low',
    speed_vs_quality_weight REAL NOT NULL DEFAULT 0.5,

    -- EMPLOYER-DEFINED RUBRIC (Sprint 3 calibration replacement for the
    -- "85% recruiter agreement" metric — employer specifies pass criteria)
    employer_rubric JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- EMBEDDING (semantic match against candidate profiles)
    requirement_embedding vector(1536)
);

CREATE TRIGGER requisitions_set_updated_at
    BEFORE UPDATE ON requisitions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX requisitions_client_idx ON requisitions (client_id);
CREATE INDEX requisitions_status_idx ON requisitions (status, urgency);
CREATE INDEX requisitions_clearance_idx ON requisitions (clearance_minimum);
CREATE INDEX requisitions_motion_idx ON requisitions (motion_type_required);
CREATE INDEX requisitions_skills_gin ON requisitions USING gin (must_have_skills);
CREATE INDEX requisitions_embedding_idx ON requisitions
    USING ivfflat (requirement_embedding vector_cosine_ops) WITH (lists = 100);
