-- Recompete events, gap analyses, alerting.

CREATE TABLE IF NOT EXISTS recompete_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    event_type          TEXT NOT NULL
        CHECK (event_type IN ('solicitation','sources_sought','award','protest','cancellation')),
    detected_date       DATE NOT NULL,
    sam_notice_id       TEXT,
    response_deadline   DATE,
    details             JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS recompete_events_contract ON recompete_events (contract_id);
CREATE INDEX IF NOT EXISTS recompete_events_event_type ON recompete_events (event_type);
CREATE UNIQUE INDEX IF NOT EXISTS recompete_events_notice_unique
    ON recompete_events (sam_notice_id) WHERE sam_notice_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS gap_analyses (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id           UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    lcat_id               UUID NOT NULL REFERENCES lcats(id) ON DELETE CASCADE,
    required_count        INTEGER NOT NULL,
    assigned_count        INTEGER NOT NULL,
    bench_available       INTEGER NOT NULL,
    gap_count             INTEGER NOT NULL,
    risk_level            TEXT NOT NULL CHECK (risk_level IN ('critical','high','watch','low')),
    estimated_fill_days   INTEGER,
    generated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS gap_analyses_contract ON gap_analyses (contract_id);
CREATE INDEX IF NOT EXISTS gap_analyses_risk ON gap_analyses (risk_level);

CREATE TABLE IF NOT EXISTS alert_rules (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name              TEXT NOT NULL,
    trigger_type      TEXT NOT NULL CHECK (trigger_type IN (
        'recompete_approaching','solicitation_detected','gap_created','gap_critical',
        'bench_threshold','bench_cost_threshold','clearance_expiring','assignment_ending'
    )),
    threshold_value   INTEGER NOT NULL DEFAULT 0,
    severity          TEXT NOT NULL DEFAULT 'warning' CHECK (severity IN ('critical','warning','info')),
    channel           TEXT NOT NULL DEFAULT 'slack' CHECK (channel IN ('slack','email','calendar')),
    recipients        TEXT[] NOT NULL DEFAULT '{}',
    is_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    cooldown_hours    INTEGER NOT NULL DEFAULT 24,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_history (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_rule_id       UUID NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    status              TEXT NOT NULL DEFAULT 'firing'
        CHECK (status IN ('firing','resolved','acknowledged')),
    message             TEXT NOT NULL,
    context             JSONB NOT NULL DEFAULT '{}'::jsonb,
    fired_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at     TIMESTAMPTZ,
    acknowledged_by     TEXT
);

CREATE INDEX IF NOT EXISTS alert_history_rule_status ON alert_history (alert_rule_id, status);
