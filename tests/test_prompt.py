"""The no-fabrication prompt is part of the product, not a comment."""

from __future__ import annotations

from pathlib import Path

from shot_ticket.images import ImageInfo
from shot_ticket.prompt import SYSTEM_PROMPT, build_user_prompt
from shot_ticket.ticket import TicketDraft


def _info() -> ImageInfo:
    return ImageInfo(
        path=Path("/tmp/login-error.png"),
        format="PNG",
        media_type="image/png",
        width=960,
        height=600,
        mode="RGB",
        size_bytes=10,
    )


def test_system_prompt_forbids_invention():
    text = SYSTEM_PROMPT
    assert "Do not invent UI text, error codes, stack traces" in text
    assert "needs confirmation" in text
    assert "unknown" in text
    assert "visible and legible" in text
    assert "Do not claim this ticket was filed" in text


def test_user_prompt_repeats_the_rule_and_lists_schema_fields():
    prompt = build_user_prompt(_info())
    assert "Do not invent UI text, error codes, or stack traces." in prompt
    assert "needs confirmation" in prompt
    for name in TicketDraft.model_fields:
        assert name in prompt
    assert "960×600" in prompt


def test_user_prompt_does_not_include_the_filename():
    info = _info()
    prompt = build_user_prompt(info)
    assert "login-error" not in prompt
    assert str(info.path) not in prompt
    assert info.path.name not in prompt
