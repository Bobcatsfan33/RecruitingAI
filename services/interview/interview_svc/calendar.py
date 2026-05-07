"""Google Calendar adapter (free OAuth)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
import structlog

log = structlog.get_logger("interview.calendar")


@dataclass
class CalendarSlot:
    start_iso: str
    end_iso: str
    timezone: str = "UTC"


@dataclass
class CalendarEvent:
    summary: str
    description: str
    attendees: list[str]
    slot: CalendarSlot
    location: str | None = None
    conference_solution: str | None = None  # e.g. hangoutsMeet


@dataclass
class CalendarEventResult:
    success: bool
    provider: str
    event_id: str | None = None
    join_url: str | None = None
    error: str | None = None


class CalendarAdapter(Protocol):
    name: str
    async def create_event(self, *, calendar_id: str, event: CalendarEvent, access_token: str) -> CalendarEventResult: ...
    async def list_busy(self, *, calendar_ids: list[str], slot: CalendarSlot, access_token: str) -> list[dict[str, Any]]: ...


class GoogleCalendarAdapter:
    """Google Calendar v3.

    Free OAuth — set GOOGLE_OAUTH_CLIENT_ID + SECRET and complete the
    OAuth dance from the candidate portal. The platform stores the
    short-lived access token + a refresh token; both are passed in here
    so the adapter is stateless.
    """

    name = "google"
    BASE = "https://www.googleapis.com/calendar/v3"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=15.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def create_event(
        self,
        *,
        calendar_id: str,
        event: CalendarEvent,
        access_token: str,
    ) -> CalendarEventResult:
        body: dict[str, Any] = {
            "summary": event.summary,
            "description": event.description,
            "start": {"dateTime": event.slot.start_iso, "timeZone": event.slot.timezone},
            "end": {"dateTime": event.slot.end_iso, "timeZone": event.slot.timezone},
            "attendees": [{"email": a} for a in event.attendees],
        }
        if event.location:
            body["location"] = event.location
        if event.conference_solution:
            body["conferenceData"] = {"createRequest": {"requestId": event.summary}}
        try:
            response = await self._client.post(
                f"{self.BASE}/calendars/{calendar_id}/events",
                params={"conferenceDataVersion": 1 if event.conference_solution else 0},
                headers={"Authorization": f"Bearer {access_token}"},
                json=body,
            )
        except httpx.HTTPError as exc:
            return CalendarEventResult(success=False, provider=self.name, error=str(exc))
        if response.status_code in (200, 201):
            data = response.json()
            join = None
            entry_points = data.get("conferenceData", {}).get("entryPoints", [])
            for ep in entry_points:
                if ep.get("entryPointType") == "video":
                    join = ep.get("uri")
                    break
            return CalendarEventResult(
                success=True, provider=self.name,
                event_id=data.get("id"),
                join_url=join or data.get("hangoutLink"),
            )
        return CalendarEventResult(
            success=False, provider=self.name, error=response.text[:200]
        )

    async def list_busy(
        self,
        *,
        calendar_ids: list[str],
        slot: CalendarSlot,
        access_token: str,
    ) -> list[dict[str, Any]]:
        body = {
            "timeMin": slot.start_iso,
            "timeMax": slot.end_iso,
            "timeZone": slot.timezone,
            "items": [{"id": cid} for cid in calendar_ids],
        }
        response = await self._client.post(
            f"{self.BASE}/freeBusy",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )
        if response.status_code != 200:
            log.warning("google_freebusy_error", status=response.status_code)
            return []
        return response.json().get("calendars", {}).values()


class MockCalendarAdapter:
    name = "mock_calendar"

    def __init__(self) -> None:
        self.events: list[CalendarEvent] = []

    async def create_event(
        self, *, calendar_id: str, event: CalendarEvent, access_token: str,
    ) -> CalendarEventResult:
        self.events.append(event)
        return CalendarEventResult(
            success=True, provider=self.name,
            event_id=f"mock-event-{len(self.events)}",
            join_url="https://meet.example.com/mock-call",
        )

    async def list_busy(
        self, *, calendar_ids: list[str], slot: CalendarSlot, access_token: str,
    ) -> list[dict[str, Any]]:
        return []


def select_calendar() -> CalendarAdapter:
    if os.environ.get("GOOGLE_OAUTH_CLIENT_ID"):
        return GoogleCalendarAdapter()
    return MockCalendarAdapter()
