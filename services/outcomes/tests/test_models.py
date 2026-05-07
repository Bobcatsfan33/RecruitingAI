"""Predictive model tests against synthetic data."""

from __future__ import annotations

from outcomes_svc.models import (
    train_offer_acceptance_model,
    train_placement_model,
)
from outcomes_svc.synthetic import (
    synthesize_offer_acceptance_dataset,
    synthesize_placement_dataset,
)


def test_placement_model_beats_random():
    rows = synthesize_placement_dataset(seed=42, n=1500)
    predictor, result = train_placement_model(rows)
    # Synthetic dataset has signal; AUC should beat 0.7.
    assert result.test_auc > 0.7


def test_offer_acceptance_model_beats_random():
    rows = synthesize_offer_acceptance_dataset(seed=7, n=1200)
    predictor, result = train_offer_acceptance_model(rows)
    assert result.test_auc > 0.7


def test_placement_predict_returns_probability():
    rows = synthesize_placement_dataset(seed=42, n=600)
    predictor, _ = train_placement_model(rows)
    p = predictor.predict_proba({
        "candidate_motion_match": 1,
        "candidate_metro_match": 1,
        "interview_avg_dim_score": 4.5,
        "req_comp_to_market_ratio": 1.05,
        "candidate_w2_verified": 1,
        "candidate_approachability_score": 80,
        "candidate_counteroffer_risk_score": 20,
        "interview_dimension_variance": 0.5,
        "screening_pass_ratio": 0.9,
    })
    assert 0.0 <= p <= 1.0


def test_explanation_returns_per_feature_contributions():
    rows = synthesize_placement_dataset(seed=42, n=600)
    predictor, _ = train_placement_model(rows)
    explanation = predictor.explain({"candidate_motion_match": 1})
    assert isinstance(explanation, dict)
    assert "candidate_motion_match" in explanation


def test_low_motivation_lowers_offer_acceptance_proba():
    rows = synthesize_offer_acceptance_dataset(seed=7, n=800)
    predictor, _ = train_offer_acceptance_model(rows)
    high_features = {
        "comp_gap_pct": 0.30, "candidate_motivation_score": 90,
        "interview_recommendation_rank": 4, "client_brand_strength": 0.9,
        "engagement_response_rate": 0.6, "candidate_counteroffer_risk_score": 20,
        "candidate_unvested_equity": 0, "current_employer_tier_rank": 0,
        "tenure_months_current_role": 12,
    }
    low_features = {
        **high_features,
        "candidate_motivation_score": 25,
        "candidate_counteroffer_risk_score": 80,
        "candidate_unvested_equity": 1,
    }
    assert predictor.predict_proba(high_features) > predictor.predict_proba(low_features)
