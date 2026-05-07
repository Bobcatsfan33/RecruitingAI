"""Feature engineering for the placement-success + offer-acceptance models.

Lightweight Feast-compatible feature names (we don't actually require
Feast at dev time but the schema mirrors it so the production migration
to a real feature store is a config change, not a rewrite).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PLACEMENT_FEATURES = [
    "candidate_clearance_rank",
    "candidate_polygraph_rank",
    "candidate_metro_match",
    "candidate_motion_match",
    "candidate_years_experience",
    "candidate_w2_verified",
    "candidate_approachability_score",
    "candidate_counteroffer_risk_score",
    "req_urgency_rank",
    "req_comp_to_market_ratio",
    "req_speed_vs_quality_weight",
    "interview_avg_dim_score",
    "interview_dimension_variance",
    "screening_pass_ratio",
    "outreach_response_rate",
]

OFFER_ACCEPTANCE_FEATURES = [
    "comp_gap_pct",
    "candidate_counteroffer_risk_score",
    "candidate_motivation_score",
    "candidate_unvested_equity",
    "current_employer_tier_rank",
    "interview_recommendation_rank",
    "client_brand_strength",
    "tenure_months_current_role",
    "engagement_response_rate",
]


@dataclass
class FeatureRow:
    feature_set: str
    features: dict[str, float] = field(default_factory=dict)
    label: int | None = None  # 1 = success / accept, 0 = fail / decline

    def vector(self, names: list[str]) -> list[float]:
        return [float(self.features.get(name, 0.0)) for name in names]


def to_feature_matrix(rows: list[FeatureRow], names: list[str]) -> list[list[float]]:
    return [row.vector(names) for row in rows]


def to_label_vector(rows: list[FeatureRow]) -> list[int]:
    return [int(row.label) if row.label is not None else 0 for row in rows]
