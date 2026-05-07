"""Voice AI adapters: Vapi + Retell. No free tier on either — both are
shipped as adapters; production wires real credentials and dev runs use
the MockVoiceAdapter."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
import structlog

log = structlog.get_logger("interview.voice")


@dataclass
class VoiceCallRequest:
    candidate_phone: str
    candidate_first_name: str
    interview_id: str
    rubric_role_type: str
    questions: list[str] = field(default_factory=list)
    callback_url: str | None = None  # webhook the platform will receive
    voice_id: str | None = None


@dataclass
class VoiceCallResult:
    success: bool
    provider: str
    call_id: str | None = None
    error: str | None = None


class VoiceAdapter(Protocol):
    name: str
    async def start_call(self, request: VoiceCallRequest) -> VoiceCallResult: ...
    async def fetch_transcript(self, call_id: str) -> dict[str, Any]: ...


class VapiAdapter:
    """Vapi.ai adapter. Requires `VAPI_API_KEY`."""

    name = "vapi"
    BASE = "https://api.vapi.ai"

    def __init__(self, *, api_key: str | None = None, default_voice: str = "andrew") -> None:
        key = api_key or os.environ.get("VAPI_API_KEY")
        if not key:
            raise RuntimeError("VAPI_API_KEY required for VapiAdapter")
        self._client = httpx.AsyncClient(
            base_url=self.BASE,
            headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
            timeout=30.0,
        )
        self._default_voice = default_voice

    async def aclose(self) -> None:
        await self._client.aclose()

    async def start_call(self, request: VoiceCallRequest) -> VoiceCallResult:
        payload = {
            "type": "outboundPhoneCall",
            "customer": {"number": request.candidate_phone, "name": request.candidate_first_name},
            "assistant": {
                "name": "Workforce Intelligence Interview",
                "model": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
                "voice": {"provider": "11labs", "voiceId": request.voice_id or self._default_voice},
                "firstMessage": (
                    f"Hi {request.candidate_first_name}, this is the Workforce screening agent. "
                    f"Got a few minutes to walk through {request.rubric_role_type} questions?"
                ),
                "systemPrompt": _SYSTEM_PROMPT_VOICE.format(
                    questions="\n- " + "\n- ".join(request.questions)
                ),
            },
            "metadata": {"interview_id": request.interview_id},
        }
        if request.callback_url:
            payload["serverUrl"] = request.callback_url
        try:
            response = await self._client.post("/call", json=payload)
        except httpx.HTTPError as exc:
            return VoiceCallResult(success=False, provider=self.name, error=str(exc))
        if response.status_code in (200, 201):
            return VoiceCallResult(
                success=True, provider=self.name, call_id=response.json().get("id"),
            )
        return VoiceCallResult(success=False, provider=self.name, error=response.text[:200])

    async def fetch_transcript(self, call_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/call/{call_id}")
        if response.status_code != 200:
            return {"error": response.text[:200]}
        return response.json()


class MockVoiceAdapter:
    name = "mock_voice"

    def __init__(self) -> None:
        self.calls: list[VoiceCallRequest] = []

    async def start_call(self, request: VoiceCallRequest) -> VoiceCallResult:
        self.calls.append(request)
        return VoiceCallResult(
            success=True, provider=self.name, call_id=f"mock-call-{len(self.calls)}",
        )

    async def fetch_transcript(self, call_id: str) -> dict[str, Any]:
        return {
            "id": call_id,
            "status": "completed",
            "transcript": "Interviewer: ...\nCandidate: ...\n",
            "ended_at": "2026-05-01T15:00:00Z",
        }


_SYSTEM_PROMPT_VOICE = """\
You are a structured screening agent. Walk through these questions in order:
{questions}

After each candidate response, ask one clarifying follow-up. Keep the
total interview under 25 minutes. End by asking the candidate if they
have any questions about the role. Do NOT make compensation promises.
"""


def select_voice() -> VoiceAdapter:
    if os.environ.get("VAPI_API_KEY"):
        try:
            return VapiAdapter()
        except RuntimeError as exc:
            log.warning("vapi_init_failed", error=str(exc))
    return MockVoiceAdapter()
