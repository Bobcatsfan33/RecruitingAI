-- Workforce graph — employees, clearances, certifications, assignments,
-- LCAT definitions tied to contracts.

CREATE TABLE IF NOT EXISTS employees (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                TEXT NOT NULL,
    email               TEXT UNIQUE NOT NULL,
    clearance_level     TEXT NOT NULL DEFAULT 'none'
        CHECK (clearance_level IN ('none','public_trust','secret','ts','ts_sci','ts_sci_poly')),
    clearance_expiry    DATE,
    poly_type           TEXT CHECK (poly_type IN ('none','ci','full_scope')),
    location            TEXT,
    education_level     TEXT CHECK (education_level IN ('HS','AA','BS','MS','PhD')),
    years_experience    INTEGER,
    skills              TEXT[] NOT NULL DEFAULT '{}',
    certifications      TEXT[] NOT NULL DEFAULT '{}',
    status              TEXT NOT NULL DEFAULT 'assigned'
        CHECK (status IN ('assigned','bench','pending_start','rolling_off')),
    bench_since         DATE,
    monthly_cost        NUMERIC(12, 2),
    source_system       TEXT,
    external_id         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS employees_clearance ON employees (clearance_level);
CREATE INDEX IF NOT EXISTS employees_status ON employees (status);
CREATE INDEX IF NOT EXISTS employees_clearance_expiry ON employees (clearance_expiry);

CREATE TABLE IF NOT EXISTS lcats (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id            UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    title                  TEXT NOT NULL,
    labor_category         TEXT,
    min_education          TEXT CHECK (min_education IN ('HS','AA','BS','MS','PhD')),
    min_experience_years   INTEGER NOT NULL DEFAULT 0,
    clearance_required     TEXT NOT NULL DEFAULT 'none'
        CHECK (clearance_required IN ('none','public_trust','secret','ts','ts_sci','ts_sci_poly')),
    location               TEXT,
    headcount              INTEGER NOT NULL DEFAULT 1,
    bill_rate_ceiling      NUMERIC(10, 2),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS lcats_contract ON lcats (contract_id);

CREATE TABLE IF NOT EXISTS lcat_requirements (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lcat_id           UUID NOT NULL REFERENCES lcats(id) ON DELETE CASCADE,
    requirement_type  TEXT NOT NULL
        CHECK (requirement_type IN ('education','experience_yrs','certification','clearance','skill')),
    value             TEXT NOT NULL,
    is_mandatory      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS lcat_requirements_lcat ON lcat_requirements (lcat_id);

CREATE TABLE IF NOT EXISTS assignments (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id   UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    contract_id   UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    lcat_id       UUID REFERENCES lcats(id) ON DELETE SET NULL,
    start_date    DATE NOT NULL,
    end_date      DATE,
    status        TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','completed','pending')),
    bill_rate     NUMERIC(10, 2),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS assignments_contract_employee ON assignments (contract_id, employee_id);
CREATE INDEX IF NOT EXISTS assignments_end_date ON assignments (end_date);

CREATE TABLE IF NOT EXISTS clearances (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id           UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    level                 TEXT NOT NULL
        CHECK (level IN ('none','public_trust','secret','ts','ts_sci','ts_sci_poly')),
    poly_type             TEXT CHECK (poly_type IN ('none','ci','full_scope')),
    investigation_date    DATE,
    expiry_date           DATE,
    adjudication_status   TEXT NOT NULL DEFAULT 'active'
        CHECK (adjudication_status IN ('active','interim','expired','revoked')),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS clearances_employee ON clearances (employee_id);

CREATE TABLE IF NOT EXISTS certifications (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id   UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    issued_date   DATE,
    expiry_date   DATE,
    status        TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','expired')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS certifications_employee ON certifications (employee_id);
