"""Interview FastAPI surface."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from interview_svc.agent import ChatTurn, InterviewAgent, InterviewSession
from interview_svc.calendar import (
    CalendarEvent,
    CalendarSlot,
    select_calendar,
)
from interview_svc.rubrics import for_role
from interview_svc.voice import VoiceCallRequest, select_voice
from wfi_audit import AuditLogger, NullAuditLogger
from wfi_llm import ModelRouter, NullModelRouter
from wfi_schemas import Scorecard

log = structlog.get_logger("interview")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


def _build_router():
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ModelRouter()
        except RuntimeError as exc:
            log.warning("router_init_failed", error=str(exc))
    return NullModelRouter(
        response_text='{"dimensions": [], "recommendation": "yes", "confidence": 0.7, '
                      '"summary": "stub", "risk_flags": [], "high_value_candidate": false}'
    )


def _build_audit():
    if os.environ.get("CLICKHOUSE_URL"):
        try:
            return AuditLogger.from_env()
        except Exception as exc:  # noqa: BLE001
            log.warning("audit_init_failed", error=str(exc))
    return NullAuditLogger()


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    _state["agent"] = InterviewAgent(router=_build_router(), audit=_build_audit())
    _state["voice"] = select_voice()
    _state["calendar"] = select_calendar()
    _state["sessions"] = {}
    log.info(
        "interview_service_started",
        voice=_state["voice"].name,
        calendar=_state["calendar"].name,
    )
    yield


app = FastAPI(title="WFI Interview", version="0.1.0", lifespan=lifespan)


class ChatStartRequest(BaseModel):
    candidate_id: UUID
    requisition_id: UUID
    role_type: str = "sales"


class ChatAnswerRequest(BaseModel):
    session_id: UUID
    content: str


class EvaluateRequest(BaseModel):
    candidate_id: UUID
    requisition_id: UUID
    role_type: str
    transcript: str | list[dict[str, Any]]


class VoiceStartRequest(BaseModel):
    candidate_phone: str
    candidate_first_name: str
    interview_id: str
    rubric_role_type: str = "sales"
    callback_url: str | None = None


class CalendarBookRequest(BaseModel):
    calendar_id: str
    summary: str
    description: str
    attendees: list[str]
    start_iso: str
    end_iso: str
    timezone: str = "UTC"
    location: str | None = None
    create_meet_link: bool = True
    access_token: str


@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/interview/chat/start")
async def chat_start(req: ChatStartRequest) -> dict[str, Any]:
    agent: InterviewAgent = _state["agent"]
    session = agent.start_chat(
        candidate_id=req.candidate_id,
        requisition_id=req.requisition_id,
        role_type=req.role_type,
    )
    _state["sessions"][session.id] = session
    return {
        "session_id": str(session.id),
        "first_question": session.turns[0].content,
        "rubric_role_type": session.rubric.role_type,
    }


@app.post("/v1/interview/chat/answer")
async def chat_answer(req: ChatAnswerRequest) -> dict[str, Any]:
    sessions: dict[UUID, InterviewSession] = _state["sessions"]
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "session not found")
    next_turn = _state["agent"].submit_answer(session, req.content)
    return {
        "session_id": str(session.id),
        "completed": session.completed,
        "next_question": next_turn.content if next_turn else None,
    }


@app.post("/v1/interview/evaluate")
async def evaluate(req: EvaluateRequest) -> Scorecard:
    rubric = for_role(req.role_type)
    transcript: list[ChatTurn] | str
    if isinstance(req.transcript, str):
        transcript = req.transcript
    else:
        transcript = [ChatTurn(role=t.get("role", "candidate"), content=t.get("content", ""))
                      for t in req.transcript]
    agent: InterviewAgent = _state["agent"]
    return await agent.evaluate_transcript(
        candidate_id=req.candidate_id,
        requisition_id=req.requisition_id,
        rubric=rubric,
        transcript=transcript,
    )


@app.post("/v1/interview/voice/start")
async def voice_start(req: VoiceStartRequest) -> dict[str, Any]:
    rubric = for_role(req.rubric_role_type)
    voice = _state["voice"]
    questions = [d.question for d in rubric.dimensions]
    result = await voice.start_call(
        VoiceCallRequest(
            candidate_phone=req.candidate_phone,
            candidate_first_name=req.candidate_first_name,
            interview_id=req.interview_id,
            rubric_role_type=req.rubric_role_type,
            questions=questions,
            callback_url=req.callback_url,
        )
    )
    return {
        "success": result.success,
        "provider": result.provider,
        "call_id": result.call_id,
        "error": result.error,
    }


@app.post("/v1/interview/calendar/book")
async def calendar_book(req: CalendarBookRequest) -> dict[str, Any]:
    cal = _state["calendar"]
    event = CalendarEvent(
        summary=req.summary,
        description=req.description,
        attendees=req.attendees,
        slot=CalendarSlot(start_iso=req.start_iso, end_iso=req.end_iso, timezone=req.timezone),
        location=req.location,
        conference_solution="hangoutsMeet" if req.create_meet_link else None,
    )
    result = await cal.create_event(
        calendar_id=req.calendar_id, event=event, access_token=req.access_token,
    )
    return {
        "success": result.success,
        "provider": result.provider,
        "event_id": result.event_id,
        "join_url": result.join_url,
        "error": result.error,
    }
