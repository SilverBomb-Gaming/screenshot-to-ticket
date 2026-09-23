"""Orchestration uses the fixed prompt and a single client call."""

from __future__ import annotations

import pytest

from shot_ticket.draft import draft_from_image
from shot_ticket.prompt import SYSTEM_PROMPT
from shot_ticket.ticket import TicketParseError
from tests.conftest import TICKET, FakeVision, TICKET_JSON


def test_draft_sends_system_prompt_and_hides_filename(login_png):
    fake = FakeVision(TICKET_JSON)
    info, ticket = draft_from_image(login_png, fake)
    assert ticket.title == TICKET["title"]
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["system"] == SYSTEM_PROMPT
    assert "Do not invent UI text" in call["system"]
    user = str(call["user"])
    assert "login-error" not in user
    assert call["image_bytes"] == login_png.read_bytes()
    assert info.path == login_png


def test_unusable_model_text_raises(login_png):
    fake = FakeVision("I invented an error code E-9999.")
    with pytest.raises(TicketParseError):
        draft_from_image(login_png, fake)
