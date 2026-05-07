"""Candidates FastAPI service.

Endpoints
---------
POST   /v1/candidates                           — manual create
POST   /v1/candidates/from-resume               — upload PDF/DOCX, parse, persist
GET    /v1/candidates/{candidate_id}            — read
GET    /v1/candidates/recent                    — list recent
POST   /v1/candidates/search                    — semantic + filter search
POST   /v1/candidates/{id}/enrich               — call enrichment adapter

POST   /v1/ownership/check                      — bundled ownership status
POST   /v1/ownership/submit                     — record a submission

GET    /v1/health                               — readiness probe
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import structlog
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from candidates_svc import candidate_repo, ownership_repo
from candidates_svc.config import get_settings
from candidates_svc.db import close_pool, init_pool
from candidates_svc.deployability import deployability_score
from candidates_svc.embeddings_text import candidate_embedding_text
from wfi_data import (
    AnthropicEmbeddingProvider,
    EmbeddingProvider,
    EnrichmentAdapter,
    MockEnrichmentAdapter,
    NullEmbeddingProvider,
    ResumeParser,
    extract_text_from_bytes,
)
from wfi_data.enrichment import ApolloEnrichmentAdapter
from wfi_llm import ModelRouter
from wfi_schemas import Candidate, CandidateSource

logging.basicConfig(level=get_settings().log_level)
log = structlog.get_logger("candidates")


def _build_embedder() -> EmbeddingProvider:
    settings = get_settings()
    if settings.voyage_api_key:
        try:
            return AnthropicEmbeddingProvider(api_key=settings.voyage_api_key)
        except RuntimeError as exc:
            log.warning("voyage_init_failed", error=str(exc))
    return NullEmbeddingProvider()


def _build_router() -> ModelRouter | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        return ModelRouter(api_key=settings.anthropic_api_key)
    except RuntimeError as exc:
        log.warning("router_init_failed", error=str(exc))
        return None


def _build_enricher() -> EnrichmentAdapter:
    settings = get_settings()
    if settings.apollo_api_key:
        try:
            return ApolloEnrichmentAdapter(api_key=settings.apollo_api_key)
        except RuntimeError as exc:
            log.warning("apollo_init_failed", error=str(exc))
    return MockEnrichmentAdapter()


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_pool()
    _state["embedder"] = _build_embedder()
    _state["router"] = _build_router()
    _state["enricher"] = _build_enricher()
    _state["resume_parser"] = ResumeParser(_state["router"])
    log.info(
        "candidates_service_started",
        embedder=type(_state["embedder"]).__name__,
        router_enabled=_state["router"] is not None,
        enricher=_state["enricher"].name,
    )
    yield
    await close_pool()


app = FastAPI(title="WFI Candidates", version="0.1.0", lifespan=lifespan)


# ---------- request / response models --------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=25, ge=1, le=100)
    clearance_minimum: str | None = None
    metro_area: str | None = None
    motion: str | None = None


class SearchHit(BaseModel):
    candidate: Candidate
    distance: float


class OwnershipCheckRequest(BaseModel):
    candidate_id: UUID
    client_id: UUID


class SubmissionRequest(BaseModel):
    candidate_id: UUID
    requisition_id: UUID
    client_id: UUID
    exclusivity_days: int = 30


# ---------- routes ----------------------------------------------------------

@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/candidates", status_code=201)
async def create_candidate(candidate: Candidate) -> dict[str, Any]:
    if not candidate.has_contact():
        raise HTTPException(400, "candidate must have email, phone, or linkedin_url")
    embedder: EmbeddingProvider = _state["embedder"]
    embedding = await embedder.embed(candidate_embedding_text(candidate))
    if candidate.clearance_type != "none":
        candidate.deployability_score = deployability_score(candidate)
    candidate_id = await candidate_repo.insert(candidate, embedding=embedding)
    return {"id": str(candidate_id)}


@app.post("/v1/candidates/from-resume", status_code=201)
async def candidate_from_resume(
    file: UploadFile = File(...),
    source: str = Form("inbound"),
) -> dict[str, Any]:
    raw = await file.read()
    text = extract_text_from_bytes(raw, filename=file.filename or "")
    if not text.strip():
        raise HTTPException(400, "could not extract text from upload")
    parser: ResumeParser = _state["resume_parser"]
    parsed = await parser.parse(text)
    if not parsed.first_name and not parsed.last_name:
        raise HTTPException(422, "resume parse produced no name")

    candidate = Candidate(
        source=CandidateSource(source),
        first_name=parsed.first_name or "Unknown",
        last_name=parsed.last_name or "Unknown",
        email=parsed.email,
        phone=parsed.phone,
        linkedin_url=parsed.linkedin_url,
        location_city=parsed.location_city,
        location_state=parsed.location_state,
        location_metro=parsed.location_metro,
        citizenship=parsed.citizenship,
        clearance_type=parsed.clearance_type,
        polygraph=parsed.polygraph,
        career_history=parsed.career_history,
        compensation_history=parsed.compensation_history,
        primary_motion=parsed.primary_motion,
        se_orientation=parsed.se_orientation,
        methodology_experience=parsed.methodology_experience,
        profile_completeness_score=int(parsed.extraction_confidence * 100),
    )
    embedder: EmbeddingProvider = _state["embedder"]
    embedding = await embedder.embed(candidate_embedding_text(candidate))
    if candidate.clearance_type != "none":
        candidate.deployability_score = deployability_score(candidate)
    candidate_id = await candidate_repo.insert(candidate, embedding=embedding)
    return {
        "id": str(candidate_id),
        "extraction_confidence": parsed.extraction_confidence,
        "fields_extracted": parsed.field_count(),
    }


@app.get("/v1/candidates/recent")
async def list_recent(limit: int = 50) -> list[Candidate]:
    return await candidate_repo.list_recent(limit=min(limit, 200))


@app.get("/v1/candidates/{candidate_id}")
async def get_candidate(candidate_id: UUID) -> Candidate:
    candidate = await candidate_repo.get(candidate_id)
    if candidate is None:
        raise HTTPException(404, "not found")
    return candidate


@app.post("/v1/candidates/search")
async def search_candidates(request: SearchRequest) -> list[SearchHit]:
    embedder: EmbeddingProvider = _state["embedder"]
    embedding = await embedder.embed(request.query)
    hits = await candidate_repo.semantic_search(
        embedding,
        limit=request.limit,
        clearance_minimum=request.clearance_minimum,
        metro_area=request.metro_area,
        motion=request.motion,
    )
    return [SearchHit(candidate=c, distance=d) for c, d in hits]


@app.post("/v1/candidates/{candidate_id}/enrich")
async def enrich_candidate(candidate_id: UUID) -> dict[str, Any]:
    candidate = await candidate_repo.get(candidate_id)
    if candidate is None:
        raise HTTPException(404, "not found")
    enricher: EnrichmentAdapter = _state["enricher"]
    if candidate.email:
        result = await enricher.enrich_by_email(candidate.email)
    elif candidate.linkedin_url:
        result = await enricher.enrich_by_linkedin(candidate.linkedin_url)
    elif candidate.first_name and candidate.last_name:
        result = await enricher.enrich_by_name_company(
            name=f"{candidate.first_name} {candidate.last_name}",
            company=candidate.career_history[0].company if candidate.career_history else "",
        )
    else:
        raise HTTPException(400, "no enrichment key available")
    return {
        "found": result.found,
        "provider": result.provider,
        "result": result.__dict__,
    }


@app.post("/v1/ownership/check")
async def ownership_check(req: OwnershipCheckRequest) -> dict[str, Any]:
    return await ownership_repo.ownership_status(req.candidate_id, req.client_id)


@app.post("/v1/ownership/submit", status_code=201)
async def ownership_submit(req: SubmissionRequest) -> dict[str, Any]:
    if await ownership_repo.has_active_exclusivity(req.candidate_id, req.client_id):
        raise HTTPException(409, "candidate under exclusivity")
    if await ownership_repo.is_dnc(req.candidate_id, req.client_id):
        raise HTTPException(409, "candidate is on DNC list")
    submission_id = await ownership_repo.record_submission(
        req.candidate_id,
        req.requisition_id,
        req.client_id,
        exclusivity_days=req.exclusivity_days,
    )
    return {"submission_id": str(submission_id)}
