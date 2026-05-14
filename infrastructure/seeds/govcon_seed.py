"""Seed sample GovCon data: 5 agencies, 8 vendors, 10 contracts, 5 LCATs,
20 employees. Idempotent — uses INSERT … ON CONFLICT DO NOTHING.

Run from the project root with::

    python -m infrastructure.seeds.govcon_seed
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4


def _u() -> UUID:
    return uuid4()


AGENCIES = [
    {"id": _u(), "name": "Department of Defense", "code": "DOD", "department": "Executive"},
    {"id": _u(), "name": "Department of Veterans Affairs", "code": "VA", "department": "Executive"},
    {"id": _u(), "name": "Department of Homeland Security", "code": "DHS", "department": "Executive"},
    {"id": _u(), "name": "Department of Health and Human Services", "code": "HHS", "department": "Executive"},
    {"id": _u(), "name": "General Services Administration", "code": "GSA", "department": "Executive"},
]

VENDORS = [
    {"id": _u(), "name": "Booz Allen Hamilton", "uei": "ZABCDE1234567",
     "size_standard": "other-than-small", "set_aside_type": "none"},
    {"id": _u(), "name": "Leidos", "uei": "ZBCDEF2345678",
     "size_standard": "other-than-small", "set_aside_type": "none"},
    {"id": _u(), "name": "ManTech International", "uei": "ZCDEFG3456789",
     "size_standard": "other-than-small", "set_aside_type": "none"},
    {"id": _u(), "name": "Octo Consulting", "uei": "ZDEFGH4567890",
     "size_standard": "small", "set_aside_type": "8a"},
    {"id": _u(), "name": "ECS Federal", "uei": "ZEFGHI5678901",
     "size_standard": "other-than-small", "set_aside_type": "none"},
    {"id": _u(), "name": "Veteran Solutions LLC", "uei": "ZFGHIJ6789012",
     "size_standard": "small", "set_aside_type": "SDVOSB"},
    {"id": _u(), "name": "HUBZone Cyber Inc", "uei": "ZGHIJK7890123",
     "size_standard": "small", "set_aside_type": "HUBZONE"},
    {"id": _u(), "name": "Wexford Group", "uei": "ZHIJKL8901234",
     "size_standard": "small", "set_aside_type": "WOSB"},
]

TODAY = date.today()


def _contracts() -> list[dict[str, Any]]:
    return [
        {
            "id": _u(),
            "piid": "FA8702-22-D-0001",
            "title": "Air Force Cloud Engineering Support",
            "description": "Cloud architecture, DevSecOps, and platform engineering for AFCEC.",
            "naics_code": "541512",
            "contract_vehicle": "GSA OASIS+",
            "agency_id": AGENCIES[0]["id"],
            "vendor_id": VENDORS[0]["id"],
            "pop_start": TODAY - timedelta(days=400),
            "pop_end": TODAY + timedelta(days=120),
            "current_value": Decimal("12_500_000.00"),
            "potential_value": Decimal("48_000_000.00"),
            "option_year": 1,
            "is_incumbent": True,
            "recompete_risk": "HIGH",
        },
        {
            "id": _u(),
            "piid": "VA-118-23-D-0042",
            "title": "VA EHR Modernization Sustainment",
            "description": "Sustainment + integration support for the Cerner EHR rollout.",
            "naics_code": "541512",
            "contract_vehicle": "VA T4NG",
            "agency_id": AGENCIES[1]["id"],
            "vendor_id": VENDORS[1]["id"],
            "pop_start": TODAY - timedelta(days=200),
            "pop_end": TODAY + timedelta(days=730),
            "current_value": Decimal("28_000_000.00"),
            "potential_value": Decimal("110_000_000.00"),
            "option_year": 0,
            "is_incumbent": True,
            "recompete_risk": "STABLE",
        },
        {
            "id": _u(),
            "piid": "70RTAC22F00000123",
            "title": "DHS CISA Threat Hunt Operations",
            "description": "Threat-hunt and incident response operations for CISA.",
            "naics_code": "541519",
            "contract_vehicle": "GSA Schedule 70",
            "agency_id": AGENCIES[2]["id"],
            "vendor_id": VENDORS[2]["id"],
            "pop_start": TODAY - timedelta(days=600),
            "pop_end": TODAY + timedelta(days=60),
            "current_value": Decimal("9_800_000.00"),
            "potential_value": Decimal("32_000_000.00"),
            "option_year": 2,
            "is_incumbent": True,
            "recompete_risk": "CRITICAL",
        },
        {
            "id": _u(),
            "piid": "HHSF223-22-C-0099",
            "title": "FDA IT Modernization Task Order",
            "description": "Application modernization, API gateway, identity migration.",
            "naics_code": "541511",
            "contract_vehicle": "CIO-SP3",
            "agency_id": AGENCIES[3]["id"],
            "vendor_id": VENDORS[3]["id"],
            "pop_start": TODAY - timedelta(days=120),
            "pop_end": TODAY + timedelta(days=900),
            "current_value": Decimal("6_400_000.00"),
            "potential_value": Decimal("24_000_000.00"),
            "option_year": 0,
            "is_incumbent": True,
            "recompete_risk": "STABLE",
        },
        {
            "id": _u(),
            "piid": "GS00Q14OADU119",
            "title": "GSA Centers of Excellence — Cloud Adoption",
            "description": "Cross-agency cloud adoption advisory.",
            "naics_code": "541611",
            "contract_vehicle": "OASIS",
            "agency_id": AGENCIES[4]["id"],
            "vendor_id": VENDORS[4]["id"],
            "pop_start": TODAY - timedelta(days=900),
            "pop_end": TODAY + timedelta(days=15),
            "current_value": Decimal("4_200_000.00"),
            "potential_value": Decimal("18_000_000.00"),
            "option_year": 4,
            "is_incumbent": True,
            "recompete_risk": "CRITICAL",
        },
        {
            "id": _u(),
            "piid": "W91WAW-23-D-0011",
            "title": "Army INSCOM Linguist Support",
            "description": "Cleared linguist services for INSCOM. TS/SCI required.",
            "naics_code": "541930",
            "contract_vehicle": "GSA Language Services",
            "agency_id": AGENCIES[0]["id"],
            "vendor_id": VENDORS[5]["id"],
            "pop_start": TODAY - timedelta(days=300),
            "pop_end": TODAY + timedelta(days=420),
            "current_value": Decimal("11_900_000.00"),
            "potential_value": Decimal("38_000_000.00"),
            "option_year": 1,
            "is_incumbent": True,
            "recompete_risk": "WATCH",
        },
        {
            "id": _u(),
            "piid": "HSHQDC-22-J-0033",
            "title": "DHS HQ Network Engineering",
            "description": "Network architecture + zero-trust rollout for DHS HQ.",
            "naics_code": "541512",
            "contract_vehicle": "EAGLE Next Gen",
            "agency_id": AGENCIES[2]["id"],
            "vendor_id": VENDORS[6]["id"],
            "pop_start": TODAY - timedelta(days=180),
            "pop_end": TODAY + timedelta(days=540),
            "current_value": Decimal("8_300_000.00"),
            "potential_value": Decimal("22_000_000.00"),
            "option_year": 0,
            "is_incumbent": True,
            "recompete_risk": "STABLE",
        },
        {
            "id": _u(),
            "piid": "75D301-23-Q-0205",
            "title": "CDC Public Health Data Engineering",
            "description": "ETL + warehouse engineering for CDC surveillance datasets.",
            "naics_code": "541512",
            "contract_vehicle": "CIO-SP3 Small Business",
            "agency_id": AGENCIES[3]["id"],
            "vendor_id": VENDORS[7]["id"],
            "pop_start": TODAY - timedelta(days=90),
            "pop_end": TODAY + timedelta(days=275),
            "current_value": Decimal("3_100_000.00"),
            "potential_value": Decimal("9_500_000.00"),
            "option_year": 0,
            "is_incumbent": True,
            "recompete_risk": "WATCH",
        },
        {
            "id": _u(),
            "piid": "FA8771-21-D-0007",
            "title": "Air Force Cyber Defense Operations",
            "description": "24x7 SOC support, threat hunting, and forensic analysis.",
            "naics_code": "541519",
            "contract_vehicle": "GSA Alliant 2",
            "agency_id": AGENCIES[0]["id"],
            "vendor_id": VENDORS[2]["id"],
            "pop_start": TODAY - timedelta(days=1100),
            "pop_end": TODAY + timedelta(days=45),
            "current_value": Decimal("19_400_000.00"),
            "potential_value": Decimal("65_000_000.00"),
            "option_year": 4,
            "is_incumbent": True,
            "recompete_risk": "CRITICAL",
        },
        {
            "id": _u(),
            "piid": "47QFCA-22-D-0190",
            "title": "GSA STARS III SDVOSB Pool",
            "description": "Multi-task STARS III pool — SDVOSB set-aside vehicle.",
            "naics_code": "541512",
            "contract_vehicle": "8(a) STARS III",
            "agency_id": AGENCIES[4]["id"],
            "vendor_id": VENDORS[5]["id"],
            "pop_start": TODAY - timedelta(days=60),
            "pop_end": TODAY + timedelta(days=1800),
            "current_value": Decimal("0.00"),
            "potential_value": Decimal("50_000_000.00"),
            "option_year": 0,
            "is_incumbent": False,
            "recompete_risk": "STABLE",
        },
    ]


def _lcats(contract_ids: list[UUID]) -> list[dict[str, Any]]:
    """Five LCATs spread across the contracts."""
    return [
        {
            "id": _u(), "contract_id": contract_ids[0], "title": "Senior Cloud Engineer",
            "labor_category": "ENG-IV", "min_education": "BS", "min_experience_years": 8,
            "clearance_required": "secret", "location": "DC Metro", "headcount": 5,
            "bill_rate_ceiling": Decimal("210.00"),
        },
        {
            "id": _u(), "contract_id": contract_ids[1], "title": "EHR Integration Engineer",
            "labor_category": "INT-III", "min_education": "BS", "min_experience_years": 6,
            "clearance_required": "public_trust", "location": "Remote", "headcount": 4,
            "bill_rate_ceiling": Decimal("175.00"),
        },
        {
            "id": _u(), "contract_id": contract_ids[2], "title": "Threat Hunt Analyst",
            "labor_category": "CYB-V", "min_education": "BS", "min_experience_years": 7,
            "clearance_required": "ts_sci", "location": "Arlington VA", "headcount": 3,
            "bill_rate_ceiling": Decimal("245.00"),
        },
        {
            "id": _u(), "contract_id": contract_ids[5], "title": "TS/SCI Linguist (Mandarin)",
            "labor_category": "LNG-IV", "min_education": "BS", "min_experience_years": 5,
            "clearance_required": "ts_sci", "location": "Fort Meade MD", "headcount": 6,
            "bill_rate_ceiling": Decimal("160.00"),
        },
        {
            "id": _u(), "contract_id": contract_ids[8], "title": "SOC Tier 3 Engineer",
            "labor_category": "CYB-IV", "min_education": "BS", "min_experience_years": 6,
            "clearance_required": "ts", "location": "San Antonio TX", "headcount": 8,
            "bill_rate_ceiling": Decimal("195.00"),
        },
    ]


_FIRST = ["Avery", "Brennan", "Casey", "Devon", "Emerson", "Finley", "Gabriel", "Harper",
          "Indira", "Jordan", "Karim", "Logan", "Maya", "Niko", "Owen", "Priya",
          "Quincy", "Reese", "Sasha", "Tariq"]
_LAST = ["Acosta", "Brooks", "Choi", "Davis", "Espinoza", "Foster", "Garcia", "Hayes",
         "Iqbal", "Jenkins", "Khan", "Lopez", "Murphy", "Nguyen", "O'Neil", "Patel",
         "Quintero", "Reyes", "Santos", "Tanaka"]


def _employees() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rng = list(range(20))
    clearances = (["ts_sci_poly"] * 2 + ["ts_sci"] * 4 + ["ts"] * 4 + ["secret"] * 6
                  + ["public_trust"] * 2 + ["none"] * 2)
    statuses = (["assigned"] * 13 + ["bench"] * 4 + ["pending_start"] * 2 + ["rolling_off"] * 1)
    locations = ["DC Metro", "Arlington VA", "Fort Meade MD", "San Antonio TX",
                 "Remote", "Tampa FL", "Huntsville AL", "Colorado Springs CO"]
    for i in rng:
        cl = clearances[i]
        rows.append({
            "id": _u(),
            "name": f"{_FIRST[i]} {_LAST[i]}",
            "email": f"{_FIRST[i].lower()}.{_LAST[i].lower().replace(chr(39),'')}@example.com",
            "clearance_level": cl,
            "clearance_expiry": (
                TODAY + timedelta(days=180 + (i * 47) % 1500) if cl != "none" else None
            ),
            "poly_type": "ci" if cl == "ts_sci_poly" else "none",
            "location": locations[i % len(locations)],
            "education_level": "BS" if i % 3 else "MS",
            "years_experience": 4 + (i * 3) % 18,
            "skills": _skills_for_index(i),
            "certifications": _certs_for_index(i),
            "status": statuses[i],
            "bench_since": (TODAY - timedelta(days=(i * 11) % 90)) if statuses[i] == "bench" else None,
            "monthly_cost": Decimal(str(11_500 + (i * 425) % 6000)),
            "source_system": "manual",
            "external_id": f"emp-{i + 1:03d}",
        })
    return rows


def _skills_for_index(i: int) -> list[str]:
    pool = [
        ["aws", "kubernetes", "terraform"],
        ["python", "fastapi", "postgres"],
        ["splunk", "sigma", "elastic"],
        ["sentinel", "azure", "kql"],
        ["mandarin", "linguistics", "translation"],
        ["incident-response", "forensics", "edr"],
        ["zero-trust", "iam", "okta"],
        ["data-engineering", "spark", "airflow"],
    ]
    return pool[i % len(pool)]


def _certs_for_index(i: int) -> list[str]:
    pool = [
        ["AWS SAA"],
        ["CISSP"],
        ["Security+", "CEH"],
        ["AZ-500"],
        ["DLPT-3 Mandarin"],
        ["GCFA", "GREM"],
        ["CCSP"],
        ["PMP"],
    ]
    return pool[i % len(pool)]


_INSERT_AGENCY = """
INSERT INTO agencies (id, name, code, department) VALUES ($1, $2, $3, $4)
ON CONFLICT (code) DO NOTHING
"""

_INSERT_VENDOR = """
INSERT INTO vendors (id, name, uei, size_standard, set_aside_type)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (uei) DO NOTHING
"""

_INSERT_CONTRACT = """
INSERT INTO contracts (
    id, piid, title, description, naics_code, contract_vehicle,
    agency_id, vendor_id, pop_start, pop_end, current_value, potential_value,
    option_year, is_incumbent, recompete_risk, source, raw_json, last_synced_at
) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,'manual',$16,$17)
ON CONFLICT (piid) DO NOTHING
"""

_INSERT_LCAT = """
INSERT INTO lcats (id, contract_id, title, labor_category, min_education,
    min_experience_years, clearance_required, location, headcount, bill_rate_ceiling)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
ON CONFLICT DO NOTHING
"""

_INSERT_EMPLOYEE = """
INSERT INTO employees (id, name, email, clearance_level, clearance_expiry,
    poly_type, location, education_level, years_experience, skills, certifications,
    status, bench_since, monthly_cost, source_system, external_id)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
ON CONFLICT (email) DO NOTHING
"""


async def seed(dsn: str) -> None:
    import asyncpg  # noqa: PLC0415

    conn = await asyncpg.connect(dsn)
    try:
        for a in AGENCIES:
            await conn.execute(_INSERT_AGENCY, a["id"], a["name"], a["code"], a["department"])
        for v in VENDORS:
            await conn.execute(
                _INSERT_VENDOR, v["id"], v["name"], v["uei"], v["size_standard"], v["set_aside_type"]
            )
        contracts = _contracts()
        for c in contracts:
            await conn.execute(
                _INSERT_CONTRACT,
                c["id"], c["piid"], c["title"], c["description"], c["naics_code"],
                c["contract_vehicle"], c["agency_id"], c["vendor_id"], c["pop_start"],
                c["pop_end"], c["current_value"], c["potential_value"], c["option_year"],
                c["is_incumbent"], c["recompete_risk"], json.dumps({"seeded": True}),
                datetime.now(UTC),
            )
        contract_ids = [c["id"] for c in contracts]
        for lc in _lcats(contract_ids):
            await conn.execute(
                _INSERT_LCAT,
                lc["id"], lc["contract_id"], lc["title"], lc["labor_category"],
                lc["min_education"], lc["min_experience_years"], lc["clearance_required"],
                lc["location"], lc["headcount"], lc["bill_rate_ceiling"],
            )
        for e in _employees():
            await conn.execute(
                _INSERT_EMPLOYEE,
                e["id"], e["name"], e["email"], e["clearance_level"], e["clearance_expiry"],
                e["poly_type"], e["location"], e["education_level"], e["years_experience"],
                e["skills"], e["certifications"], e["status"], e["bench_since"],
                e["monthly_cost"], e["source_system"], e["external_id"],
            )
        print(f"seeded {len(AGENCIES)} agencies, {len(VENDORS)} vendors, "
              f"{len(contracts)} contracts, {len(_lcats(contract_ids))} lcats, "
              f"{len(_employees())} employees")
    finally:
        await conn.close()


def main() -> None:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://wfi:wfi@localhost:5432/workforce_intelligence",
    )
    asyncio.run(seed(dsn))


if __name__ == "__main__":  # pragma: no cover
    main()
