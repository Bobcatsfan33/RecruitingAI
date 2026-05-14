"""Audit logging — every mutating route emits an audit event."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4


def _contract(piid: str):
    return {
        "piid": piid,
        "title": f"Contract {piid}",
        "naics_code": "541512",
        "agency_id": str(uuid4()),
        "vendor_id": str(uuid4()),
        "pop_start": str(date.today()),
        "pop_end": str(date.today() + timedelta(days=180)),
    }


def test_contract_create_emits_audit_with_resource_id(client, audit):
    r = client.post("/v1/contracts", json=_contract("AUDIT-001"))
    body = r.json()
    matches = [e for e in audit.events if e.action == "contract.create"]
    assert matches, "expected contract.create audit event"
    assert matches[-1].resource_type == "contract"
    assert matches[-1].resource_id == body["id"]
    assert matches[-1].detail.get("piid") == "AUDIT-001"


def test_contract_update_emits_audit_with_field_list(client, audit):
    created = client.post("/v1/contracts", json=_contract("AUDIT-002")).json()
    client.patch(
        f"/v1/contracts/{created['id']}",
        json={"recompete_risk": "CRITICAL"},
    )
    matches = [e for e in audit.events if e.action == "contract.update"]
    assert matches
    assert matches[-1].detail.get("fields") == ["recompete_risk"]


def test_employee_create_emits_audit(client, audit):
    client.post(
        "/v1/workforce/employees",
        json={
            "name": "Audit Test", "email": "audit@example.com",
            "clearance_level": "secret", "status": "assigned",
        },
    )
    actions = [e.action for e in audit.events]
    assert "employee.create" in actions
