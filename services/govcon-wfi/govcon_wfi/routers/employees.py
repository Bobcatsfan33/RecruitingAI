"""Workforce CRUD — employees with clearance / status filtering."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from wfi_schemas import Employee, EmployeeCreate, EmployeeUpdate

from govcon_wfi.db import get_database
from govcon_wfi.deps import AuditEvent, get_audit

router = APIRouter(prefix="/v1/workforce", tags=["workforce"])


class EmployeeListResponse(BaseModel):
    items: list[Employee]
    total: int
    page: int
    page_size: int


def _to_employee(row: dict[str, Any]) -> Employee:
    return Employee.model_validate(row)


@router.post("/employees", response_model=Employee, status_code=201)
async def create_employee(body: EmployeeCreate) -> Employee:
    db = get_database()
    audit = get_audit()
    existing = await db.list_rows("employees", filters={"email": body.email}, limit=1)
    if existing:
        raise HTTPException(409, f"employee with email {body.email} already exists")
    payload = body.model_dump(mode="python")
    row = await db.insert_returning("employees", list(payload.keys()), list(payload.values()))
    employee = _to_employee(row)
    await audit.record(
        AuditEvent(
            actor="api",
            action="employee.create",
            resource_type="employee",
            resource_id=str(employee.id),
            detail={"email": body.email, "clearance_level": str(body.clearance_level)},
        )
    )
    return employee


@router.get("/employees/{employee_id}", response_model=Employee)
async def get_employee(employee_id: UUID) -> Employee:
    db = get_database()
    row = await db.get_row("employees", "id", employee_id)
    if row is None:
        raise HTTPException(404, "employee not found")
    return _to_employee(row)


@router.patch("/employees/{employee_id}", response_model=Employee)
async def update_employee(employee_id: UUID, body: EmployeeUpdate) -> Employee:
    db = get_database()
    audit = get_audit()
    diff = body.model_dump(exclude_unset=True, mode="python")
    if not diff:
        existing = await db.get_row("employees", "id", employee_id)
        if existing is None:
            raise HTTPException(404, "employee not found")
        return _to_employee(existing)
    updated = await db.update_returning(
        "employees", "id", employee_id, list(diff.keys()), list(diff.values())
    )
    if updated is None:
        raise HTTPException(404, "employee not found")
    await audit.record(
        AuditEvent(
            actor="api",
            action="employee.update",
            resource_type="employee",
            resource_id=str(employee_id),
            detail={"fields": list(diff.keys())},
        )
    )
    return _to_employee(updated)


@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(
    status: str | None = Query(default=None),
    clearance_level: str | None = Query(default=None),
    location: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> EmployeeListResponse:
    db = get_database()
    rows = await db.list_rows("employees", limit=10_000, offset=0)
    if status:
        rows = [r for r in rows if str(r.get("status")) == status]
    if clearance_level:
        rows = [r for r in rows if str(r.get("clearance_level")) == clearance_level]
    if location:
        loc = location.lower()
        rows = [r for r in rows if loc in (r.get("location") or "").lower()]
    total = len(rows)
    start = (page - 1) * page_size
    sliced = rows[start : start + page_size]
    return EmployeeListResponse(
        items=[_to_employee(r) for r in sliced],
        total=total,
        page=page,
        page_size=page_size,
    )
