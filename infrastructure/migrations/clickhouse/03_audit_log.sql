-- Immutable audit log: every AI decision recorded for EEOC/OFCCP/compliance.
-- Append-only by convention; we use ReplacingMergeTree only to deduplicate
-- on log_id when an at-least-once delivery causes a re-write.

CREATE TABLE IF NOT EXISTS workforce_analytics.audit_log (
    log_id UUID,
    timestamp DateTime64(3) DEFAULT now64(3),
    action_type Enum(
        'screen_decision' = 1,
        'score_assigned' = 2,
        'submission_decision' = 3,
        'outreach_sent' = 4,
        'interview_evaluation' = 5,
        'offer_recommendation' = 6,
        'routing_decision' = 7,
        'escalation_triggered' = 8,
        'compliance_check' = 9,
        'rule_evaluation' = 10
    ),
    candidate_id UUID,
    requisition_id Nullable(UUID),
    agent_type LowCardinality(String),
    model_used LowCardinality(String),
    input_summary String,
    decision String,
    reasoning String,
    confidence_score Float32,
    human_override Nullable(Bool),
    override_by Nullable(String),
    override_reason Nullable(String),
    cost_usd Nullable(Float32),
    latency_ms Nullable(UInt32)
)
ENGINE = ReplacingMergeTree
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, action_type, log_id)
TTL timestamp + INTERVAL 7 YEAR;

-- Materialised view: daily counts per action_type / agent for ops dashboards.
CREATE MATERIALIZED VIEW IF NOT EXISTS workforce_analytics.audit_log_daily_mv
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(day)
ORDER BY (day, action_type, agent_type)
AS
SELECT
    toDate(timestamp) AS day,
    action_type,
    agent_type,
    count() AS decisions,
    sum(cost_usd) AS total_cost_usd,
    avg(confidence_score) AS avg_confidence
FROM workforce_analytics.audit_log
GROUP BY day, action_type, agent_type;
