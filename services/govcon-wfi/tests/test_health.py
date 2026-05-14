"""Health endpoints + placeholder routes return the expected statuses."""

from __future__ import annotations

import pytest


def test_health_ok(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_live(client):
    assert client.get("/v1/health/live").status_code == 200


def test_ready(client):
    assert client.get("/v1/health/ready").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/v1/recompetes",
        "/v1/lcats",
        "/v1/gaps",
        "/v1/bench",
        "/v1/alerts",
        "/v1/auth",
    ],
)
def test_placeholder_routes_501(client, path):
    assert client.get(path).status_code == 501
