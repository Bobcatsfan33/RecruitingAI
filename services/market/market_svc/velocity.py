"""Hiring velocity reports — demand signals for skills, clearances, roles."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class HiringSignal:
    timestamp: datetime
    skill: str | None = None
    clearance: str | None = None
    role_type: str | None = None
    location: str | None = None


@dataclass
class VelocityReport:
    skill_demand_30d: dict[str, int]
    skill_demand_90d: dict[str, int]
    clearance_demand_30d: dict[str, int]
    role_type_demand_30d: dict[str, int]
    location_demand_30d: dict[str, int]
    momentum: dict[str, float]  # skill -> 30d / 90d ratio


def report(signals: list[HiringSignal], *, now: datetime | None = None) -> VelocityReport:
    now = now or datetime.now(timezone.utc)
    cutoff_30 = now - timedelta(days=30)
    cutoff_90 = now - timedelta(days=90)

    skill_30 = Counter[str]()
    skill_90 = Counter[str]()
    clearance_30 = Counter[str]()
    role_30 = Counter[str]()
    location_30 = Counter[str]()
    for sig in signals:
        ts = sig.timestamp.astimezone(timezone.utc)
        if ts < cutoff_90:
            continue
        if sig.skill and ts >= cutoff_90:
            skill_90[sig.skill] += 1
            if ts >= cutoff_30:
                skill_30[sig.skill] += 1
        if ts >= cutoff_30:
            if sig.clearance:
                clearance_30[sig.clearance] += 1
            if sig.role_type:
                role_30[sig.role_type] += 1
            if sig.location:
                location_30[sig.location] += 1

    momentum: dict[str, float] = {}
    for skill, count_30 in skill_30.items():
        count_90 = skill_90.get(skill, 0) or 1
        momentum[skill] = round(count_30 * 3.0 / count_90, 4)  # *3 to normalise to monthly

    return VelocityReport(
        skill_demand_30d=dict(skill_30),
        skill_demand_90d=dict(skill_90),
        clearance_demand_30d=dict(clearance_30),
        role_type_demand_30d=dict(role_30),
        location_demand_30d=dict(location_30),
        momentum=momentum,
    )
