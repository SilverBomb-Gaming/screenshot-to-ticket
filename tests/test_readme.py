"""The README is the install guide. Keep the required promises in it."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_no_html_comments_and_covers_the_contract():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "<!--" not in text
    assert "In the owner's words" in text
    for needle in (
        "local-first",
        "ollama pull llava",
        "SHOT_TICKET_PROVIDER",
        "SHOT_TICKET_MODEL",
        "SHOT_TICKET_BASE_URL",
        "SHOT_TICKET_API_KEY",
        "PNG",
        "JPEG",
        "WebP",
        "PDF",
        "pytest",
        "--dry-run",
        "Jira",
        "GitHub Issues",
        "shot-ticket draft --image samples/login-error.png",
    ):
        assert needle in text, needle


def test_license_and_entrypoint_are_present():
    assert (ROOT / "LICENSE").is_file()
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'shot-ticket = "shot_ticket.cli:main"' in project
    assert 'name = "screenshot-to-ticket"' in project
