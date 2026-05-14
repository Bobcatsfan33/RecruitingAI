"""Workforce CRUD."""

from __future__ import annotations

from uuid import uuid4


def _payload(email: str | None = None, **overrides):
    base = {
        "name": "Test Employee",
        "email": email or f"test-{uuid4()}@example.com",
        "clearance_level": "secret",
        "location": "DC Metro",
        "education_level": "BS",
        "years_experience": 7,
        "skills": ["python", "aws"],
        "certifications": ["Security+"],
        "status": "assigned",
    }
    base.update(overrides)
    return base


def test_create_employee(client, audit):
    r = client.post("/v1/workforce/employees", json=_payload(email="alpha@example.com"))
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "alpha@example.com"
    assert any(e.action == "employee.create" for e in audit.events)


def test_duplicate_email_returns_409(client):
    client.post("/v1/workforce/employees", json=_payload(email="dup@example.com"))
    r = client.post("/v1/workforce/employees", json=_payload(email="dup@example.com"))
    assert r.status_code == 409


def test_get_employee(client):
    created = client.post("/v1/workforce/employees", json=_payload()).json()
    r = client.get(f"/v1/workforce/employees/{created['id']}")
    assert r.status_code == 200


def test_patch_employee_updates_status(client, audit):
    created = client.post("/v1/workforce/employees", json=_payload()).json()
    r = client.patch(
        f"/v1/workforce/employees/{created['id']}",
        json={"status": "bench", "bench_since": "2026-01-15"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "bench"
    assert any(e.action == "employee.update" for e in audit.events)


def test_list_employees_filter_by_status(client):
    client.post("/v1/workforce/employees", json=_payload(email="a@e.com", status="assigned"))
    client.post("/v1/workforce/employees", json=_payload(email="b@e.com", status="bench"))
    r = client.get("/v1/workforce/employees?status=bench")
    statuses = {it["status"] for it in r.json()["items"]}
    assert "bench" in statuses


def test_list_employees_filter_by_clearance(client):
    client.post("/v1/workforce/employees", json=_payload(email="ts1@e.com", clearance_level="ts_sci"))
    client.post("/v1/workforce/employees", json=_payload(email="s1@e.com", clearance_level="secret"))
    r = client.get("/v1/workforce/employees?clearance_level=ts_sci")
    levels = {it["clearance_level"] for it in r.json()["items"]}
    assert "ts_sci" in levels and "secret" not in levels
