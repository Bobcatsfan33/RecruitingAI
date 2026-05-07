"""Silver-medalist pool tests."""

from __future__ import annotations

from uuid import uuid4

from pipeline_svc.silver import SilverPool


def test_hold_assigns_sequential_ranks():
    pool = SilverPool()
    req = uuid4()
    a = pool.hold(req, uuid4())
    b = pool.hold(req, uuid4())
    c = pool.hold(req, uuid4())
    assert (a.rank, b.rank, c.rank) == (1, 2, 3)


def test_promote_pops_rank_one_and_renumbers():
    pool = SilverPool()
    req = uuid4()
    pool.hold(req, uuid4())
    cand_2 = uuid4()
    pool.hold(req, cand_2)
    cand_3 = uuid4()
    pool.hold(req, cand_3)
    promoted = pool.promote_next(req)
    assert promoted is not None
    assert promoted.rank == 1
    health = pool.health(req)
    assert health["active_silver_count"] == 2
    assert health["ranks"] == [1, 2]


def test_promote_returns_none_when_pool_empty():
    pool = SilverPool()
    assert pool.promote_next(uuid4()) is None


def test_release_removes_specific_candidate():
    pool = SilverPool()
    req = uuid4()
    pool.hold(req, uuid4())
    target = uuid4()
    pool.hold(req, target)
    pool.hold(req, uuid4())
    pool.release(req, target)
    health = pool.health(req)
    assert health["active_silver_count"] == 2
