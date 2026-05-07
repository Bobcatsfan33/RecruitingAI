"""Repo-root conftest: every package + service is on sys.path so pytest can
discover tests without a published install."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for sub in [
    "packages/py-schemas",
    "packages/py-data",
    "packages/py-llm",
    "packages/py-events",
    "packages/py-audit",
    "packages/py-rules-sdk",
    "services/candidates",
    "services/rules",
    "services/screening",
    "services/outreach",
    "services/pipeline",
    "services/client-advisory",
    "services/interview",
    "services/capture",
    "services/outcomes",
    "services/bench",
    "services/market",
]:
    path = ROOT / sub
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))
