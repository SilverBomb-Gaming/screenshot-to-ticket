"""Prompts for the vision model.

The system prompt is a product constraint: the draft may quote only what is
legible in the screenshot. Tests lock the wording so a refactor cannot
quietly drop it.
"""

from __future__ import annotations

from shot_ticket.images import ImageInfo

SYSTEM_PROMPT = """\
You draft one bug ticket from one screenshot. Return a single JSON object and nothing else.

Rules you must follow:
- Use only UI text, error codes, and stack traces that are visible and legible in the image.
- Do not invent UI text, error codes, stack traces, labels, URLs, or personal data that are not visible or not legible.
- If you are unsure, write "unknown" and say the field needs confirmation. Do not fill in blurry or cut-off characters.
- Severity is a guess based only on visible impact. Use "unknown" when you cannot tell.
- Steps to reproduce must come from what the screen shows. Do not describe clicks or pages that are not visible.
- Do not claim this ticket was filed in any tracker.
"""

_JSON_SHAPE = """\
{
  "title": "unknown",
  "severity": "unknown",
  "steps_to_reproduce": ["unknown — needs confirmation"],
  "expected": "unknown",
  "actual": "unknown",
  "environment_notes": ["unknown — needs confirmation"],
  "unknowns": ["expected"],
  "visible_text": []
}
"""


def build_user_prompt(info: ImageInfo) -> str:
    """Instructions that sit beside the image.

    The file name is intentionally omitted. A name like ``login-error.png``
    is not on-screen evidence, and the model must not treat it as such.
    """
    return (
        "Read the attached screenshot and fill the ticket JSON.\n"
        "Do not invent UI text, error codes, or stack traces. "
        'If a detail is missing or illegible, use "unknown" and note that it needs confirmation.\n'
        f"The image is {info.format}, {info.width}×{info.height} pixels. "
        "Those facts are file metadata, not text painted in the UI.\n"
        "Replace every placeholder below with evidence from the image. "
        "Keep unknown where the image does not show the answer.\n"
        "severity must be one of: unknown, low, medium, high, critical.\n"
        "visible_text must list only exact legible strings copied from the image, or be empty.\n"
        "Return JSON only, with these keys:\n"
        f"{_JSON_SHAPE}"
    )
