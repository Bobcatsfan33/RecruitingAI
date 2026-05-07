"""Tests for the resume parser regex pre-pass + extraction pipeline."""

from __future__ import annotations

import pytest

from wfi_data.resume import (
    ResumeParser,
    extract_text_from_bytes,
    parse_docx_bytes,
    parse_pdf_bytes,
)
from wfi_data.resume import _regex_pre_extract


def test_regex_extracts_email_phone_linkedin():
    text = """
    Jane Doe
    jane.doe@example.com  +1 (555) 123-4567
    https://www.linkedin.com/in/janedoe
    """
    out = _regex_pre_extract(text)
    assert out["email"] == "jane.doe@example.com"
    assert out["phone"].endswith("5551234567")
    assert out["linkedin_url"].endswith("/in/janedoe")


def test_regex_detects_clearance_levels():
    cases = {
        "Active TS/SCI with CI Polygraph": ("ts_sci", "ci"),
        "Top Secret cleared engineer, lifestyle polygraph": ("top_secret", "lifestyle"),
        "Secret clearance with FullScope Polygraph": ("secret", "full_scope"),
        "Public Trust": ("public_trust", None),
        "No clearance mentioned here": (None, None),
    }
    for text, (clearance, poly) in cases.items():
        out = _regex_pre_extract(text)
        if clearance is None:
            assert "clearance_type" not in out
        else:
            assert out["clearance_type"] == clearance
        if poly is None:
            assert "polygraph" not in out
        else:
            assert out["polygraph"] == poly


def test_extract_text_handles_empty_input():
    assert extract_text_from_bytes(b"") == ""


def test_extract_text_falls_back_to_utf8():
    out = extract_text_from_bytes(b"plain ascii resume", filename="resume.txt")
    assert "plain ascii" in out


def test_parse_pdf_bytes_returns_empty_for_garbage():
    assert parse_pdf_bytes(b"not a pdf") == ""


def test_parse_docx_bytes_returns_empty_for_garbage():
    assert parse_docx_bytes(b"not a docx") == ""


@pytest.mark.asyncio
async def test_parser_without_router_returns_regex_only():
    parser = ResumeParser(router=None)
    result = await parser.parse(
        "Jane Doe\njane@example.com\n+1-555-555-1212\n"
        "TS/SCI clearance, CI poly. AE at Datadog 2020-2024."
    )
    # Without LLM we still get the regex hits.
    assert result.email == "jane@example.com"
    assert result.clearance_type == "ts_sci"
    assert result.polygraph == "ci"


@pytest.mark.asyncio
async def test_parser_handles_blank_input():
    parser = ResumeParser(router=None)
    result = await parser.parse("   ")
    assert result.first_name == ""
    assert result.extraction_confidence == 0.0
