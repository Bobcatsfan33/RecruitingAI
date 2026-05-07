CREATE TABLE IF NOT EXISTS workforce_analytics.interaction_events (
    event_id UUID,
    timestamp DateTime64(3) DEFAULT now64(3),
    event_type Enum(
        'outreach_sent' = 1,
        'outreach_opened' = 2,
        'outreach_clicked' = 3,
        'outreach_replied' = 4,
        'screen_started' = 5,
        'screen_completed' = 6,
        'interview_scheduled' = 7,
        'interview_completed' = 8,
        'submission_sent' = 9,
        'feedback_received' = 10,
        'offer_extended' = 11,
        'offer_accepted' = 12,
        'offer_declined' = 13,
        'candidate_started' = 14,
        'candidate_falloff' = 15,
        'placement_90day' = 16,
        'referral_received' = 17,
        'profile_updated' = 18,
        'enrichment_completed' = 19
    ),
    candidate_id UUID,
    requisition_id Nullable(UUID),
    client_id Nullable(UUID),
    agent_type Enum(
        'sourcer' = 1,
        'screening' = 2,
        'outreach' = 3,
        'interview' = 4,
        'pipeline_manager' = 5,
        'compliance' = 6,
        'bench_management' = 7,
        'client_advisory' = 8,
        'close_protection' = 9,
        'client_development' = 10,
        'system' = 99
    ),
    channel Nullable(Enum(
        'email' = 1,
        'linkedin' = 2,
        'phone' = 3,
        'sms' = 4,
        'voice_ai' = 5,
        'chat' = 6,
        'portal' = 7
    )),
    metadata String,
    outcome Nullable(Enum(
        'positive' = 1,
        'negative' = 2,
        'neutral' = 3,
        'pending' = 4
    )),
    cost_usd Nullable(Float32),
    duration_seconds Nullable(UInt32)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, event_type, candidate_id)
TTL timestamp + INTERVAL 5 YEAR;
