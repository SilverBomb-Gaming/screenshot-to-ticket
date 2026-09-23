"""Shared fixtures. Nothing here contacts a model server."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"

TICKET = {
    "title": "Sign-in failed on FixtureApp",
    "severity": "medium",
    "steps_to_reproduce": [
        "Open the FixtureApp sign-in screen.",
        "Enter an email and password.",
        "Choose Sign in.",
    ],
    "expected": "unknown — needs confirmation",
    "actual": "A banner reads: Sign-in failed. Check the email and password.",
    "environment_notes": ["unknown — needs confirmation"],
    "unknowns": ["expected result", "browser and operating system"],
    "visible_text": [
        "Sign-in failed. Check the email and password.",
        "Sign in",
    ],
}

TICKET_JSON = json.dumps(TICKET)


class FakeVision:
    """In-memory stand-in for a vision client."""

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    def complete(self, *, system: str, user: str, image: object, image_bytes: bytes) -> str:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "image": image,
                "image_bytes": image_bytes,
            }
        )
        return self.payload


@pytest.fixture
def login_png() -> Path:
    return SAMPLES / "login-error.png"


@pytest.fixture
def checkout_png() -> Path:
    return SAMPLES / "checkout-total.png"
