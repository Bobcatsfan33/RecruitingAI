"""Synthetic training data generator.

Per the build constraint, the platform has no real placements. We
generate a labelled synthetic dataset that follows plausible statistical
relationships so the models train and produce sensible predictions.
"""

from __future__ import annotations

import random

from outcomes_svc.features import FeatureRow


def synthesize_placement_dataset(*, seed: int = 42, n: int = 1500) -> list[FeatureRow]:
    rng = random.Random(seed)
    rows: list[FeatureRow] = []
    for _ in range(n):
        clearance = rng.randint(0, 4)
        poly = rng.randint(0, 3)
        metro_match = rng.choice([0, 1])
        motion_match = rng.choice([0, 1])
        years = rng.randint(1, 25)
        w2_verified = rng.choice([0, 1])
        approach = rng.randint(20, 95)
        counter_risk = rng.randint(10, 90)
        urgency = rng.randint(0, 3)
        comp_ratio = round(rng.uniform(0.6, 1.4), 3)
        speed_weight = round(rng.uniform(0.0, 1.0), 3)
        interview_avg = round(rng.uniform(2.0, 5.0), 2)
        interview_var = round(rng.uniform(0.0, 2.0), 2)
        screening = round(rng.uniform(0.5, 1.0), 3)
        outreach = round(rng.uniform(0.05, 0.45), 3)

        # Heuristic generative model — placement success is positively
        # correlated with motion_match, metro_match, interview score,
        # comp_ratio, w2_verified, approachability, lower counter risk.
        score = (
            0.20 * motion_match
            + 0.15 * metro_match
            + 0.30 * (interview_avg - 2.0) / 3.0
            + 0.15 * (comp_ratio - 0.6)
            + 0.10 * w2_verified
            + 0.10 * (approach / 100.0)
            - 0.20 * (counter_risk / 100.0)
            - 0.05 * (interview_var / 2.0)
            + rng.gauss(0, 0.15)
        )
        label = 1 if score > 0.45 else 0
        rows.append(FeatureRow(
            feature_set="placement_success",
            features={
                "candidate_clearance_rank": clearance,
                "candidate_polygraph_rank": poly,
                "candidate_metro_match": metro_match,
                "candidate_motion_match": motion_match,
                "candidate_years_experience": years,
                "candidate_w2_verified": w2_verified,
                "candidate_approachability_score": approach,
                "candidate_counteroffer_risk_score": counter_risk,
                "req_urgency_rank": urgency,
                "req_comp_to_market_ratio": comp_ratio,
                "req_speed_vs_quality_weight": speed_weight,
                "interview_avg_dim_score": interview_avg,
                "interview_dimension_variance": interview_var,
                "screening_pass_ratio": screening,
                "outreach_response_rate": outreach,
            },
            label=label,
        ))
    return rows


def synthesize_offer_acceptance_dataset(*, seed: int = 7, n: int = 1200) -> list[FeatureRow]:
    rng = random.Random(seed)
    rows: list[FeatureRow] = []
    for _ in range(n):
        comp_gap = round(rng.uniform(-0.10, 0.45), 3)
        counter_risk = rng.randint(10, 90)
        motivation = rng.randint(20, 100)
        unvested = rng.choice([0, 1])
        current_tier = rng.randint(0, 3)
        interview_rec = rng.randint(0, 4)  # 0=strong_no, 4=strong_yes
        brand = round(rng.uniform(0.3, 1.0), 3)
        tenure = rng.randint(2, 84)
        response_rate = round(rng.uniform(0.05, 0.7), 3)

        # Positive correlations: comp_gap, motivation, interview_rec, brand,
        # response_rate. Negative: counter_risk, unvested, current_tier, tenure.
        score = (
            0.30 * comp_gap
            + 0.20 * (motivation / 100.0)
            + 0.15 * (interview_rec / 4.0)
            + 0.10 * brand
            + 0.10 * response_rate
            - 0.20 * (counter_risk / 100.0)
            - 0.10 * unvested
            - 0.10 * (current_tier / 3.0)
            - 0.05 * (tenure / 84.0)
            + rng.gauss(0, 0.12)
        )
        label = 1 if score > 0.20 else 0
        rows.append(FeatureRow(
            feature_set="offer_acceptance",
            features={
                "comp_gap_pct": comp_gap,
                "candidate_counteroffer_risk_score": counter_risk,
                "candidate_motivation_score": motivation,
                "candidate_unvested_equity": unvested,
                "current_employer_tier_rank": current_tier,
                "interview_recommendation_rank": interview_rec,
                "client_brand_strength": brand,
                "tenure_months_current_role": tenure,
                "engagement_response_rate": response_rate,
            },
            label=label,
        ))
    return rows
