"""GET /v1/contracts/{id} returns the full graph (agency, vendor, lcats, etc)."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from govcon_wfi.ingestors.upsert import upsert_agency, upsert_vendor

pytestmark = pytest.mark.asyncio


async def test_detail_returns_envelope_and_related_entities(client, db):
    # Insert agency + vendor first.
    agency_id = await upsert_agency(name="DOD", code="DOD")
    vendor_id = await upsert_vendor(name="Booz Allen", uei="BAH123456789")

    payload = {
        "piid": "DETAIL-001",
        "title": "Cloud Engineering",
        "description": "Multi-cloud platform engineering",
        "naics_code": "541512",
        "agency_id": str(agency_id),
        "vendor_id": str(vendor_id),
        "pop_start": str(date.today()),
        "pop_end": str(date.today() + timedelta(days=365)),
    }
    created = client.post("/v1/contracts", json=payload).json()

    detail = client.get(f"/v1/contracts/{created['id']}").json()
    assert detail["contract"]["piid"] == "DETAIL-001"
    assert detail["agency"] is not None
    assert detail["agency"]["name"] == "DOD"
    assert detail["vendor"]["name"] == "Booz Allen"
    assert detail["lcats"] == []
    assert detail["recompete_events"] == []
    assert detail["assignments"] == []
    assert detail["gap_analyses"] == []


async def test_detail_404(client):
    assert client.get(f"/v1/contracts/{uuid4()}").status_code == 404
