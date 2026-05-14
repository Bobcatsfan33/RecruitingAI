-- GovCon-side audit log: every mutating API call (contract create / update,
-- employee create / update, alert fire, sync run) gets one row here.
-- Separated from the recruiting audit_log because the resource shape differs.

CREATE TABLE IF NOT EXISTS workforce_analytics.govcon_audit_log (
    log_id          UUID,
    timestamp       DateTime64(3) DEFAULT now64(3),
    actor           LowCardinality(String),
    action          LowCardinality(String),
    resource_type   LowCardinality(String),
    resource_id     String,
    detail_json     String
)
ENGINE = ReplacingMergeTree
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, action, resource_type, log_id)
TTL timestamp + INTERVAL 7 YEAR;

CREATE MATERIALIZED VIEW IF NOT EXISTS workforce_analytics.govcon_audit_log_daily_mv
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(day)
ORDER BY (day, action, resource_type)
AS
SELECT
    toDate(timestamp) AS day,
    action,
    resource_type,
    count() AS events
FROM workforce_analytics.govcon_audit_log
GROUP BY day, action, resource_type;
