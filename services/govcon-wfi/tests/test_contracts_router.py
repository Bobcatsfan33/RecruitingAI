"""Contracts CRUD + listing + filters + semantic search."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest


def _payload(piid: str, **overrides):
    base = {
        "piid": piid,
        "title": f"Contract {piid}",
        "description": "Cloud engineering and DevSecOps support",
        "naics_code": "541512",
        "contract_vehicle": "OASIS+",
        "agency_id": str(uuid4()),
        "vendor_id": str(uuid4()),
        "pop_start": str(date.today() - timedelta(days=30)),
        "pop_end": str(date.today() + timedelta(days=180)),
        "current_value": "1000000.00",
        "potential_value": "5000000.00",
        "option_year": 0,
        "base_or_option": "base",
        "is_incumbent": True,
        "recompete_risk": "WATCH",
        "status": "active",
        "source": "manual",
    }
    base.update(overrides)
    return base


def test_create_contract_returns_201_and_records_audit(client, audit):
    r = client.post("/v1/contracts", json=_payload("PIID-001"))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["piid"] == "PIID-001"
    assert body["title"] == "Contract PIID-001"
    assert any(e.action == "contract.create" for e in audit.events)


def test_duplicate_piid_returns_409(client):
    client.post("/v1/contracts", json=_payload("PIID-002"))
    r = client.post("/v1/contracts", json=_payload("PIID-002"))
    assert r.status_code == 409


def test_get_contract_returns_full_detail(client):
    created = client.post("/v1/contracts", json=_payload("PIID-003")).json()
    r = client.get(f"/v1/contracts/{created['id']}")
    assert r.status_code == 200
    assert r.json()["piid"] == "PIID-003"


def test_get_unknown_returns_404(client):
    r = client.get(f"/v1/contracts/{uuid4()}")
    assert r.status_code == 404


def test_patch_contract_updates_fields_and_audits(client, audit):
    created = client.post("/v1/contracts", json=_payload("PIID-004")).json()
    r = client.patch(
        f"/v1/contracts/{created['id']}",
        json={"recompete_risk": "CRITICAL", "status": "active"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["recompete_risk"] == "CRITICAL"
    assert any(e.action == "contract.update" for e in audit.events)


def test_list_contracts_returns_envelope(client):
    for i in range(3):
        client.post("/v1/contracts", json=_payload(f"PIID-LIST-{i}"))
    r = client.get("/v1/contracts")
    body = r.json()
    assert body["total"] >= 3
    assert "items" in body
    assert body["page"] == 1
    assert body["page_size"] == 50


def test_filter_by_naics(client):
    client.post("/v1/contracts", json=_payload("PIID-N1", naics_code="541512"))
    client.post("/v1/contracts", json=_payload("PIID-N2", naics_code="541611"))
    r = client.get("/v1/contracts?naics=541611")
    items = r.json()["items"]
    assert {it["piid"] for it in items} >= {"PIID-N2"}
    assert all(it["naics_code"] == "541611" for it in items)


def test_filter_by_pop_end_before(client):
    client.post(
        "/v1/contracts",
        json=_payload("PIID-EXPIRING-SOON", pop_end=str(date.today() + timedelta(days=10))),
    )
    client.post(
        "/v1/contracts",
        json=_payload("PIID-EXPIRING-LATER", pop_end=str(date.today() + timedelta(days=600))),
    )
    cutoff = date.today() + timedelta(days=30)
    r = client.get(f"/v1/contracts?pop_end_before={cutoff.isoformat()}")
    piids = {it["piid"] for it in r.json()["items"]}
    assert "PIID-EXPIRING-SOON" in piids
    assert "PIID-EXPIRING-LATER" not in piids


def test_filter_by_risk(client):
    client.post("/v1/contracts", json=_payload("PIID-R1", recompete_risk="CRITICAL"))
    client.post("/v1/contracts", json=_payload("PIID-R2", recompete_risk="STABLE"))
    r = client.get("/v1/contracts?risk=CRITICAL")
    piids = {it["piid"] for it in r.json()["items"]}
    assert "PIID-R1" in piids and "PIID-R2" not in piids


def test_text_search_q_filter(client):
    client.post(
        "/v1/contracts",
        json=_payload("PIID-Q1", title="DevSecOps Pipeline Build", description="Jenkins, Argo, Spinnaker"),
    )
    client.post(
        "/v1/contracts",
        json=_payload("PIID-Q2", title="Mobile App Development", description="iOS Swift only"),
    )
    r = client.get("/v1/contracts?q=Spinnaker")
    piids = {it["piid"] for it in r.json()["items"]}
    assert piids == {"PIID-Q1"}


def test_semantic_search_returns_results(client):
    client.post("/v1/contracts", json=_payload("PIID-S1"))
    client.post("/v1/contracts", json=_payload("PIID-S2"))
    r = client.get("/v1/contracts?semantic_q=cloud%20engineering")
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1


def test_pagination_respected(client):
    for i in range(7):
        client.post("/v1/contracts", json=_payload(f"PIID-PAGE-{i:02d}"))
    r = client.get("/v1/contracts?page_size=3&page=2")
    body = r.json()
    assert body["page"] == 2
    assert body["page_size"] == 3
    assert len(body["items"]) <= 3


def test_invalid_sort_returns_400(client):
    r = client.get("/v1/contracts?sort=bogus")
    assert r.status_code == 400


@pytest.mark.parametrize("missing", ["piid", "title"])
def test_missing_required_fields_returns_422(client, missing):
    body = _payload("PIID-X")
    body.pop(missing)
    r = client.post("/v1/contracts", json=body)
    assert r.status_code == 422
