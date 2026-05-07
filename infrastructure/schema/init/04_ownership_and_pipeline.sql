-- Ownership tables: submissions, RTR, DNC, non-compete + non-solicit.
-- Pipeline state tables: pipeline events, silver-medalist buffers.

CREATE TYPE submission_status AS ENUM (
    'draft', 'submitted', 'in_review', 'screen_scheduled', 'screened',
    'interview_scheduled', 'interviewed', 'offer_extended',
    'offer_accepted', 'offer_declined', 'started', 'no_show',
    'fall_off', 'rejected', 'withdrawn'
);

CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    requisition_id UUID NOT NULL REFERENCES requisitions(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    status submission_status NOT NULL DEFAULT 'draft',
    submitted_at TIMESTAMPTZ,
    -- exclusivity expires at submitted_at + N (typically 30-90 days per client contract)
    exclusivity_expires_at TIMESTAMPTZ,
    submission_package JSONB,
    feedback JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (candidate_id, client_id, requisition_id)
);

CREATE TRIGGER submissions_set_updated_at
    BEFORE UPDATE ON submissions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX submissions_candidate_idx ON submissions (candidate_id);
CREATE INDEX submissions_req_idx ON submissions (requisition_id);
CREATE INDEX submissions_status_idx ON submissions (status);
CREATE INDEX submissions_exclusivity_idx ON submissions (exclusivity_expires_at)
    WHERE exclusivity_expires_at IS NOT NULL;

-- Right To Represent — signed acknowledgement candidate gives the agency
CREATE TABLE rights_to_represent (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    document_url TEXT,
    revoked_at TIMESTAMPTZ,
    UNIQUE (candidate_id, client_id, signed_at)
);

CREATE INDEX rtr_active_idx ON rights_to_represent (candidate_id, client_id, expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE do_not_contact (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    -- NULL client_id = global DNC across all clients
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX dnc_lookup_idx ON do_not_contact (candidate_id, client_id);

CREATE TABLE non_competes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    source_company TEXT NOT NULL,
    jurisdiction TEXT NOT NULL, -- two-letter state code
    expires_at TIMESTAMPTZ,
    scope JSONB NOT NULL DEFAULT '{}'::jsonb, -- {industries, customers, geography}
    enforceability TEXT, -- banned | restricted | enforceable (per state)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX non_competes_candidate_idx ON non_competes (candidate_id, expires_at);

CREATE TABLE non_solicits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    source_company TEXT NOT NULL,
    expires_at TIMESTAMPTZ,
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX non_solicits_candidate_idx ON non_solicits (candidate_id, expires_at);

-- Silver-medalist buffer (Sprint 5): backfill candidates kept warm at the
-- penultimate stage so a falloff can be replaced inside 48h.
CREATE TABLE silver_medalists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requisition_id UUID NOT NULL REFERENCES requisitions(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    rank SMALLINT NOT NULL DEFAULT 1, -- 1 = first backup, 2 = second, etc.
    held_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    promoted_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    UNIQUE (requisition_id, candidate_id)
);

CREATE INDEX silver_medalists_active_idx ON silver_medalists (requisition_id, rank)
    WHERE promoted_at IS NULL AND released_at IS NULL;

-- Pipeline event log (relational mirror; ClickHouse holds the analytical copy)
CREATE TABLE pipeline_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    requisition_id UUID REFERENCES requisitions(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor TEXT -- agent name, user id, or 'system'
);

CREATE INDEX pipeline_events_candidate_idx ON pipeline_events (candidate_id, occurred_at DESC);
CREATE INDEX pipeline_events_req_idx ON pipeline_events (requisition_id, occurred_at DESC);
