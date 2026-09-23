"""Schema parsing and local markdown/JSON rendering."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shot_ticket.images import ImageInfo
from shot_ticket.ticket import TicketDraft, TicketParseError, parse_model_output, render_ticket
from tests.conftest import TICKET, TICKET_JSON

INFO = ImageInfo(
    path=Path("samples/login-error.png"),
    format="PNG",
    media_type="image/png",
    width=960,
    height=600,
    mode="RGB",
    size_bytes=128,
)


def test_parse_valid_ticket():
    ticket = parse_model_output(TICKET_JSON)
    assert ticket.title == "Sign-in failed on FixtureApp"
    assert ticket.severity.value == "medium"
    assert len(ticket.steps_to_reproduce) == 3


def test_severity_is_case_insensitive():
    payload = dict(TICKET, severity="High")
    ticket = parse_model_output(json.dumps(payload))
    assert ticket.severity.value == "high"


def test_single_string_steps_are_coerced():
    payload = dict(TICKET, steps_to_reproduce="Open the sign-in screen.")
    ticket = parse_model_output(json.dumps(payload))
    assert ticket.steps_to_reproduce == ["Open the sign-in screen."]


def test_extra_fields_are_ignored():
    payload = dict(TICKET, confidence=0.2, stack_trace="invented")
    ticket = parse_model_output(json.dumps(payload))
    assert ticket.title == TICKET["title"]
    assert "confidence" not in ticket.model_dump()


def test_fenced_and_preambled_json():
    fenced = "```json\n" + TICKET_JSON + "\n```"
    preambled = "Here is the draft:\n" + TICKET_JSON + "\nDone."
    assert parse_model_output(fenced).title == TICKET["title"]
    assert parse_model_output(preambled).actual.startswith("A banner reads")


def test_rejects_missing_title():
    payload = dict(TICKET)
    del payload["title"]
    with pytest.raises(TicketParseError, match="title"):
        parse_model_output(json.dumps(payload))


def test_rejects_blank_title_and_blank_steps():
    with pytest.raises(TicketParseError, match="title"):
        parse_model_output(json.dumps(dict(TICKET, title="   ")))
    with pytest.raises(TicketParseError, match="steps_to_reproduce"):
        parse_model_output(json.dumps(dict(TICKET, steps_to_reproduce=["  "])))


def test_rejects_unknown_severity_and_non_object():
    with pytest.raises(TicketParseError, match="severity"):
        parse_model_output(json.dumps(dict(TICKET, severity="severe")))
    with pytest.raises(TicketParseError, match="JSON object"):
        parse_model_output("no json here")
    with pytest.raises(TicketParseError, match="must be an object"):
        parse_model_output("[1, 2, 3]")


def test_title_newlines_collapse():
    ticket = TicketDraft.model_validate(dict(TICKET, title="Sign-in\nfailed"))
    assert ticket.title == "Sign-in failed"


def test_markdown_has_stable_sections_and_does_not_claim_filing():
    markdown = render_ticket(parse_model_output(TICKET_JSON), INFO, "markdown")
    for heading in (
        "# Sign-in failed on FixtureApp",
        "## Steps to reproduce",
        "## Expected",
        "## Actual",
        "## Environment notes",
        "## Visible text",
        "## Needs confirmation",
    ):
        assert heading in markdown
    assert "shot-ticket did not file this anywhere" in markdown
    assert "medium (guess — confirm)" in markdown
    assert "1. Open the FixtureApp sign-in screen." in markdown
    assert "Draft file only." in markdown


def test_unknown_severity_asks_for_confirmation():
    ticket = parse_model_output(json.dumps(dict(TICKET, severity="unknown")))
    markdown = render_ticket(ticket, INFO, "markdown")
    assert "unknown — needs confirmation" in markdown


def test_empty_visible_text_and_unknowns_have_placeholders():
    payload = dict(TICKET, visible_text=[], unknowns=[])
    markdown = render_ticket(parse_model_output(json.dumps(payload)), INFO, "markdown")
    assert "None confidently read." in markdown
    assert "None noted." in markdown


def test_json_render_adds_screenshot_metadata_only():
    payload = json.loads(render_ticket(parse_model_output(TICKET_JSON), INFO, "json"))
    assert payload["title"] == TICKET["title"]
    assert payload["severity"] == "medium"
    assert payload["screenshot"] == {
        "filename": "login-error.png",
        "format": "PNG",
        "media_type": "image/png",
        "width": 960,
        "height": 600,
    }
    assert "dry_run" not in payload
    assert "stack_trace" not in payload
