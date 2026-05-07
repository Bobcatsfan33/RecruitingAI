"""Channel adapter tests — MockChannel + select_channel fallback."""

from __future__ import annotations

import pytest

from outreach_svc.channels import MockChannel, OutreachMessage, select_channel


@pytest.mark.asyncio
async def test_mock_channel_captures_sends():
    channel = MockChannel()
    msg = OutreachMessage(to="a@b.local", subject="hi", body_text="hello")
    out = await channel.send(msg)
    assert out.success
    assert channel.sent == [msg]


def test_select_channel_returns_smtp_when_no_sendgrid_key(monkeypatch):
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    chan = select_channel("email")
    assert chan.channel_type == "email"


def test_select_channel_falls_back_to_mock_for_sms(monkeypatch):
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    chan = select_channel("sms")
    assert chan.channel_type == "sms"
    assert "mock" in chan.name


def test_select_channel_returns_linkedin_mock():
    chan = select_channel("linkedin")
    assert chan.channel_type == "linkedin"
    assert "mock" in chan.name


def test_unknown_channel_raises():
    with pytest.raises(ValueError):
        select_channel("carrier_pigeon")
