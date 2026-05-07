"""Voice + calendar adapter tests."""

from __future__ import annotations

import pytest

from interview_svc.calendar import (
    CalendarEvent,
    CalendarSlot,
    MockCalendarAdapter,
    select_calendar,
)
from interview_svc.voice import (
    MockVoiceAdapter,
    VoiceCallRequest,
    select_voice,
)


@pytest.mark.asyncio
async def test_mock_voice_returns_call_id():
    adapter = MockVoiceAdapter()
    out = await adapter.start_call(
        VoiceCallRequest(
            candidate_phone="+15551234567",
            candidate_first_name="Sam",
            interview_id="i-1",
            rubric_role_type="sales",
            questions=["q1", "q2"],
        )
    )
    assert out.success
    assert out.call_id and out.call_id.startswith("mock-call-")


@pytest.mark.asyncio
async def test_mock_voice_transcript_returns_completed():
    adapter = MockVoiceAdapter()
    out = await adapter.fetch_transcript("call-1")
    assert out["status"] == "completed"


@pytest.mark.asyncio
async def test_mock_calendar_creates_event():
    adapter = MockCalendarAdapter()
    out = await adapter.create_event(
        calendar_id="primary",
        event=CalendarEvent(
            summary="Screen w/ Sam",
            description="20m chat",
            attendees=["sam@example.com", "alex@workforce.local"],
            slot=CalendarSlot(start_iso="2026-05-10T15:00:00Z", end_iso="2026-05-10T15:20:00Z"),
            conference_solution="hangoutsMeet",
        ),
        access_token="dev",
    )
    assert out.success
    assert out.join_url


def test_select_voice_falls_back_to_mock(monkeypatch):
    monkeypatch.delenv("VAPI_API_KEY", raising=False)
    assert isinstance(select_voice(), MockVoiceAdapter)


def test_select_calendar_falls_back_to_mock(monkeypatch):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    assert isinstance(select_calendar(), MockCalendarAdapter)
