"""Ticket schema and local rendering.

Markdown headings are produced here, not by the model, so the file shape
stays stable even when the vision model is chatty.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shot_ticket.images import ImageInfo


class TicketParseError(ValueError):
    """The model response was not a ticket JSON object."""


class Severity(str, Enum):
    unknown = "unknown"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


def _as_str_list(value: object) -> object:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return value


def _clean_items(value: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in value:
        flat = " ".join(item.split())
        if flat:
            cleaned.append(flat)
    return cleaned


class TicketDraft(BaseModel):
    """Structured draft. Unknowns stay explicit instead of being guessed away."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    title: str = Field(min_length=1)
    severity: Severity
    steps_to_reproduce: list[str] = Field(min_length=1)
    expected: str = Field(min_length=1)
    actual: str = Field(min_length=1)
    environment_notes: list[str] = Field(min_length=1)
    unknowns: list[str] = Field(default_factory=list)
    visible_text: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _one_line_title(cls, value: str) -> str:
        flat = " ".join(value.split())
        if not flat:
            raise ValueError("title is empty")
        return flat

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator(
        "steps_to_reproduce",
        "environment_notes",
        "unknowns",
        "visible_text",
        mode="before",
    )
    @classmethod
    def _listify(cls, value: object) -> object:
        return _as_str_list(value)

    @field_validator("steps_to_reproduce", "environment_notes")
    @classmethod
    def _required_items(cls, value: list[str]) -> list[str]:
        cleaned = _clean_items(value)
        if not cleaned:
            raise ValueError("at least one non-empty item is required")
        return cleaned

    @field_validator("unknowns", "visible_text")
    @classmethod
    def _optional_items(cls, value: list[str]) -> list[str]:
        return _clean_items(value)


def extract_json_object(text: str) -> str:
    """Pull a JSON value out of a model reply.

    A bare array is returned as-is so the caller can reject it. When the
    reply has prose around an object, the outermost ``{...}`` is returned.
    """
    stripped = _strip_fences(text)
    try:
        json.loads(stripped)
        return stripped
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end <= start:
        array_start = stripped.find("[")
        array_end = stripped.rfind("]")
        if array_start != -1 and array_end > array_start:
            return stripped[array_start : array_end + 1]
        raise TicketParseError("Model response did not contain a JSON object.")
    return stripped[start : end + 1]


def parse_model_output(text: str) -> TicketDraft:
    blob = extract_json_object(text)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise TicketParseError(f"Model returned invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise TicketParseError("Model JSON must be an object.")
    try:
        return TicketDraft.model_validate(data)
    except ValidationError as exc:
        detail = "; ".join(_validation_bits(exc))
        raise TicketParseError(
            f"Model JSON did not match the ticket schema: {detail}"
        ) from exc


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _validation_bits(exc: ValidationError) -> list[str]:
    bits: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "ticket"
        bits.append(f"{location}: {error['msg']}")
    return bits


def render_markdown(ticket: TicketDraft, info: ImageInfo) -> str:
    severity = _severity_line(ticket.severity)
    steps = "\n".join(
        f"{index}. {step}" for index, step in enumerate(ticket.steps_to_reproduce, start=1)
    )
    environment = "\n".join(f"- {note}" for note in ticket.environment_notes)
    visible = _bullets(ticket.visible_text, empty="None confidently read.")
    unknowns = _bullets(ticket.unknowns, empty="None noted.")
    filename = info.path.name

    return (
        f"# {ticket.title}\n"
        "\n"
        f"> Draft only, from `{filename}`. shot-ticket did not file this anywhere. "
        "Severity is a guess. If a line says unknown or needs confirmation, "
        "check the screenshot before you trust it.\n"
        "\n"
        f"**Severity (guess):** {severity}\n"
        f"**Screenshot:** {filename} · {info.format} · {info.width}×{info.height}\n"
        "\n"
        "## Steps to reproduce\n"
        "\n"
        f"{steps}\n"
        "\n"
        "## Expected\n"
        "\n"
        f"{ticket.expected}\n"
        "\n"
        "## Actual\n"
        "\n"
        f"{ticket.actual}\n"
        "\n"
        "## Environment notes\n"
        "\n"
        f"{environment}\n"
        "\n"
        "## Visible text\n"
        "\n"
        "Only strings the model claims are legible in the image:\n"
        "\n"
        f"{visible}\n"
        "\n"
        "## Needs confirmation\n"
        "\n"
        f"{unknowns}\n"
        "\n"
        "---\n"
        "\n"
        "Draft file only. Review it before copying into an issue tracker.\n"
    )


def render_json(ticket: TicketDraft, info: ImageInfo) -> str:
    payload: dict[str, Any] = ticket.model_dump(mode="json")
    payload["screenshot"] = {
        "filename": info.path.name,
        "format": info.format,
        "media_type": info.media_type,
        "width": info.width,
        "height": info.height,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_ticket(ticket: TicketDraft, info: ImageInfo, output_format: str) -> str:
    if output_format == "markdown":
        return render_markdown(ticket, info)
    if output_format == "json":
        return render_json(ticket, info)
    raise ValueError(f"Unsupported format: {output_format}")


def _severity_line(severity: Severity) -> str:
    if severity is Severity.unknown:
        return "unknown — needs confirmation"
    return f"{severity.value} (guess — confirm)"


def _bullets(items: list[str], *, empty: str) -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)
