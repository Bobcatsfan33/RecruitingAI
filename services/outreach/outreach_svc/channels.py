"""Outreach channel adapters: SMTP (free), SendGrid (free dev tier), Twilio,
LinkedIn (mock — no public API access without partner status).

Every adapter implements ``OutreachChannel`` so the sequence engine doesn't
have to know which one is wired up.
"""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

import httpx
import structlog

log = structlog.get_logger("outreach.channels")


@dataclass
class OutreachMessage:
    to: str
    subject: str
    body_text: str
    body_html: str | None = None
    from_addr: str = "outreach@local"
    reply_to: str | None = None
    headers: dict[str, str] | None = None


@dataclass
class DeliveryResult:
    success: bool
    provider: str
    channel: str
    message_id: str | None = None
    error: str | None = None


class OutreachChannel(Protocol):
    name: str
    channel_type: str  # email | sms | linkedin
    async def send(self, message: OutreachMessage) -> DeliveryResult: ...


# ---------- email channels --------------------------------------------------


class SmtpChannel:
    """SMTP — works against the dockerised mailpit by default."""

    name = "smtp"
    channel_type = "email"

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        starttls: bool = False,
    ) -> None:
        self._host = host or os.environ.get("SMTP_HOST", "localhost")
        self._port = port or int(os.environ.get("SMTP_PORT", "1025"))
        self._username = username or os.environ.get("SMTP_USERNAME") or None
        self._password = password or os.environ.get("SMTP_PASSWORD") or None
        self._starttls = starttls

    async def send(self, message: OutreachMessage) -> DeliveryResult:
        try:
            mime = MIMEMultipart("alternative")
            mime["From"] = message.from_addr
            mime["To"] = message.to
            mime["Subject"] = message.subject
            if message.reply_to:
                mime["Reply-To"] = message.reply_to
            for key, value in (message.headers or {}).items():
                mime[key] = value
            mime.attach(MIMEText(message.body_text, "plain"))
            if message.body_html:
                mime.attach(MIMEText(message.body_html, "html"))

            with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
                if self._starttls:
                    smtp.starttls()
                if self._username and self._password:
                    smtp.login(self._username, self._password)
                smtp.sendmail(message.from_addr, [message.to], mime.as_string())
            return DeliveryResult(
                success=True,
                provider=self.name,
                channel=self.channel_type,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("smtp_send_failed", to=message.to, error=str(exc))
            return DeliveryResult(
                success=False,
                provider=self.name,
                channel=self.channel_type,
                error=str(exc),
            )


class SendGridChannel:
    """SendGrid v3 client. Free tier exists for low-volume dev sends."""

    name = "sendgrid"
    channel_type = "email"
    BASE = "https://api.sendgrid.com/v3"

    def __init__(self, *, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("SENDGRID_API_KEY")
        if not key:
            raise RuntimeError("SENDGRID_API_KEY required for SendGridChannel")
        self._key = key
        self._client = httpx.AsyncClient(
            base_url=self.BASE,
            headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
            timeout=20.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send(self, message: OutreachMessage) -> DeliveryResult:
        payload: dict = {
            "personalizations": [{"to": [{"email": message.to}], "subject": message.subject}],
            "from": {"email": message.from_addr},
            "content": [{"type": "text/plain", "value": message.body_text}],
        }
        if message.body_html:
            payload["content"].append({"type": "text/html", "value": message.body_html})
        if message.reply_to:
            payload["reply_to"] = {"email": message.reply_to}
        try:
            response = await self._client.post("/mail/send", json=payload)
        except httpx.HTTPError as exc:
            return DeliveryResult(
                success=False, provider=self.name, channel=self.channel_type, error=str(exc)
            )
        if response.status_code in (202, 200):
            return DeliveryResult(
                success=True,
                provider=self.name,
                channel=self.channel_type,
                message_id=response.headers.get("X-Message-Id"),
            )
        return DeliveryResult(
            success=False,
            provider=self.name,
            channel=self.channel_type,
            error=response.text[:200],
        )


# ---------- SMS / LinkedIn (mock-only without paid integration) -------------


class TwilioSmsChannel:
    """Twilio SMS — no free tier. Requires SID + token."""

    name = "twilio"
    channel_type = "sms"

    def __init__(
        self,
        *,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
    ) -> None:
        sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
        token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
        if not sid or not token:
            raise RuntimeError("TWILIO_ACCOUNT_SID/AUTH_TOKEN required")
        self._sid = sid
        self._token = token
        self._from = from_number or os.environ.get("TWILIO_FROM_NUMBER", "")
        self._client = httpx.AsyncClient(timeout=15.0, auth=(sid, token))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send(self, message: OutreachMessage) -> DeliveryResult:
        try:
            response = await self._client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json",
                data={"To": message.to, "From": self._from, "Body": message.body_text},
            )
        except httpx.HTTPError as exc:
            return DeliveryResult(
                success=False, provider=self.name, channel=self.channel_type, error=str(exc)
            )
        if response.status_code in (200, 201):
            return DeliveryResult(
                success=True,
                provider=self.name,
                channel=self.channel_type,
                message_id=response.json().get("sid"),
            )
        return DeliveryResult(
            success=False, provider=self.name, channel=self.channel_type,
            error=response.text[:200],
        )


class MockChannel:
    """Captures sends in memory. Used for dev + tests; also returned by
    ``select_channel`` when the requested channel has no credentials."""

    def __init__(self, *, name: str = "mock", channel_type: str = "email") -> None:
        self.name = name
        self.channel_type = channel_type
        self.sent: list[OutreachMessage] = []

    async def send(self, message: OutreachMessage) -> DeliveryResult:
        self.sent.append(message)
        return DeliveryResult(
            success=True,
            provider=self.name,
            channel=self.channel_type,
            message_id=f"mock-{len(self.sent)}",
        )


def select_channel(channel_type: str) -> OutreachChannel:
    """Pick the best concrete adapter based on env. Always returns an adapter
    (mock when nothing is configured)."""
    if channel_type == "email":
        if os.environ.get("SENDGRID_API_KEY"):
            try:
                return SendGridChannel()
            except RuntimeError:
                pass
        return SmtpChannel()
    if channel_type == "sms":
        if os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN"):
            try:
                return TwilioSmsChannel()
            except RuntimeError:
                pass
        return MockChannel(name="twilio_mock", channel_type="sms")
    if channel_type == "linkedin":
        return MockChannel(name="linkedin_mock", channel_type="linkedin")
    raise ValueError(f"unknown channel_type {channel_type}")
