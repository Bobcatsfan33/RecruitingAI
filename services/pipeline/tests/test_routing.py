"""Multi-req routing tests."""

from __future__ import annotations

from uuid import uuid4

from pipeline_svc.routing import CandidateView, RequisitionView, route


def _embedding(weights: dict[int, float], dim: int = 8) -> list[float]:
    vec = [0.0] * dim
    for idx, w in weights.items():
        vec[idx] = w
    return vec


def test_route_filters_by_clearance_floor():
    candidate = CandidateView(embedding=_embedding({0: 1.0}), clearance="secret", motion=None, metro=None)
    req_ts = RequisitionView(
        id=uuid4(),
        embedding=_embedding({0: 1.0}),
        clearance_minimum="ts_sci",
        motion_required=None,
        metro=None,
    )
    matches = route(candidate, [req_ts])
    assert matches == []


def test_route_returns_high_similarity_match():
    candidate = CandidateView(embedding=_embedding({0: 1.0}), clearance="ts_sci", motion="enterprise", metro="DC Metro")
    req = RequisitionView(
        id=uuid4(),
        embedding=_embedding({0: 1.0}),
        clearance_minimum="secret",
        motion_required="enterprise",
        metro="DC Metro",
    )
    matches = route(candidate, [req])
    assert len(matches) == 1
    assert matches[0].score > 0.99
    assert matches[0].matches_motion is True
    assert matches[0].matches_metro is True


def test_route_orders_by_score_desc():
    candidate = CandidateView(embedding=_embedding({0: 1.0}), clearance="ts_sci", motion=None, metro=None)
    req_a = RequisitionView(id=uuid4(), embedding=_embedding({0: 1.0}), clearance_minimum="none", motion_required=None, metro=None)
    req_b = RequisitionView(id=uuid4(), embedding=_embedding({0: 0.5, 1: 0.5}), clearance_minimum="none", motion_required=None, metro=None)
    matches = route(candidate, [req_a, req_b])
    assert matches[0].requisition_id == req_a.id


def test_route_score_floor_can_be_overridden():
    candidate = CandidateView(embedding=_embedding({0: 1.0}), clearance="ts_sci", motion=None, metro=None)
    req = RequisitionView(id=uuid4(), embedding=_embedding({1: 1.0}), clearance_minimum="none", motion_required=None, metro=None)
    assert route(candidate, [req]) == []
    assert route(candidate, [req], score_floor=-1.0) != []
