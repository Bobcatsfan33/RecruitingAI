"""Repo-root conftest: every active package + service is on sys.path so pytest
can discover tests without a published install.

Frozen services (screening, outreach, pipeline, client-advisory, interview,
outcomes, market, candidates) live in the tree for reference but are NOT
imported and their tests are excluded via ``norecursedirs`` below.
"""

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
    "services/govcon-wfi",
    "services/rules",
    "services/capture",
    "services/bench",
]:
    path = ROOT / sub
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))


# Skip frozen services + the candidate portal app from collection.
collect_ignore_glob = [
    "services/screening/*",
    "services/outreach/*",
    "services/pipeline/*",
    "services/client-advisory/*",
    "services/interview/*",
    "services/outcomes/*",
    "services/market/*",
    "services/candidates/*",
    "apps/candidate-portal/*",
]
