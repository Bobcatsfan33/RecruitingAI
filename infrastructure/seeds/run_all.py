"""Load synthetic candidates into the running PG instance.

Usage::
    uv run python -m infrastructure.seeds.run_all --count 500
"""

from __future__ import annotations

import argparse
import asyncio

import structlog
from candidates_svc import candidate_repo
from candidates_svc.db import close_pool, init_pool
from candidates_svc.deployability import deployability_score
from candidates_svc.embeddings_text import candidate_embedding_text
from wfi_data import NullEmbeddingProvider

from infrastructure.seeds.synthetic import synthetic_candidates

log = structlog.get_logger("seeds.run_all")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    await init_pool()
    embedder = NullEmbeddingProvider()
    inserted = 0
    try:
        for candidate in synthetic_candidates(seed=args.seed, count=args.count):
            embedding = await embedder.embed(candidate_embedding_text(candidate))
            if candidate.clearance_type != "none":
                candidate.deployability_score = deployability_score(candidate)
            await candidate_repo.insert(candidate, embedding=embedding)
            inserted += 1
            if inserted % 50 == 0:
                log.info("seeded", inserted=inserted)
    finally:
        await close_pool()
    log.info("seed_complete", inserted=inserted)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
