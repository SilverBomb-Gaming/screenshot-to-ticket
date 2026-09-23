"""Turn one validated screenshot into a ticket draft."""

from __future__ import annotations

from pathlib import Path

from shot_ticket.images import ImageInfo, inspect_image
from shot_ticket.prompt import SYSTEM_PROMPT, build_user_prompt
from shot_ticket.ticket import TicketDraft, parse_model_output
from shot_ticket.vision import VisionClient


def draft_from_info(info: ImageInfo, client: VisionClient) -> TicketDraft:
    """Call the vision client once and parse a ticket. ``info`` is already validated."""
    raw = client.complete(
        system=SYSTEM_PROMPT,
        user=build_user_prompt(info),
        image=info,
        image_bytes=info.path.read_bytes(),
    )
    return parse_model_output(raw)


def draft_from_image(path: Path, client: VisionClient) -> tuple[ImageInfo, TicketDraft]:
    """Validate ``path``, call the vision client once, and parse the ticket."""
    info = inspect_image(path)
    return info, draft_from_info(info, client)
