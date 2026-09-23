"""Validate screenshot files and describe them."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 15 * 1024 * 1024

# Extension -> Pillow format names we accept for that suffix.
_EXTENSION_FORMATS: dict[str, frozenset[str]] = {
    ".png": frozenset({"PNG"}),
    ".jpg": frozenset({"JPEG"}),
    ".jpeg": frozenset({"JPEG"}),
    ".webp": frozenset({"WEBP"}),
}

_MEDIA_TYPES = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}


class ImageError(ValueError):
    """The path is missing, unsupported, or not a readable screenshot."""


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    format: str
    media_type: str
    width: int
    height: int
    mode: str
    size_bytes: int


def inspect_image(path: Path) -> ImageInfo:
    """Open a PNG, JPEG, or WebP file and return factual metadata.

    The filename is not interpreted. Callers that talk to a model should
    avoid forwarding ``path`` so a suggestive name cannot leak into the draft.
    """
    if not path.exists():
        raise ImageError(f"Image not found: {path}")
    if not path.is_file():
        raise ImageError(f"Image path is not a file: {path}")

    extension = path.suffix.lower()
    allowed = _EXTENSION_FORMATS.get(extension)
    if allowed is None:
        raise ImageError(
            "Unsupported image type "
            f"'{extension or '(no extension)'}'. "
            "Supported types: PNG, JPEG, and WebP."
        )

    size_bytes = path.stat().st_size
    if size_bytes == 0:
        raise ImageError(f"Image file is empty: {path}")
    if size_bytes > MAX_IMAGE_BYTES:
        raise ImageError(
            f"Image is {size_bytes} bytes, over the limit of {MAX_IMAGE_BYTES} bytes."
        )

    try:
        with Image.open(path) as image:
            image.load()
            pillow_format = image.format
            width, height = image.size
            mode = image.mode
    except UnidentifiedImageError as exc:
        raise ImageError(f"Could not read image file: {path}") from exc
    except OSError as exc:
        raise ImageError(f"Could not read image file: {path}") from exc

    if pillow_format not in allowed:
        found = pillow_format or "unknown"
        raise ImageError(
            f"File content is {found}, which does not match the {extension} extension. "
            "Supported types: PNG, JPEG, and WebP."
        )

    return ImageInfo(
        path=path,
        format=pillow_format,
        media_type=_MEDIA_TYPES[pillow_format],
        width=width,
        height=height,
        mode=mode,
        size_bytes=size_bytes,
    )


def render_metadata(info: ImageInfo, output_format: str) -> str:
    """Format dry-run metadata. No model fields are included."""
    if output_format == "json":
        payload = {
            "dry_run": True,
            "model_called": False,
            "image": str(info.path),
            "format": info.format,
            "media_type": info.media_type,
            "width": info.width,
            "height": info.height,
            "mode": info.mode,
            "size_bytes": info.size_bytes,
        }
        return json.dumps(payload, indent=2) + "\n"

    if output_format == "markdown":
        return (
            "# Dry run\n"
            "\n"
            "No model was called.\n"
            "\n"
            f"- **Image:** {info.path}\n"
            f"- **Format:** {info.format}\n"
            f"- **Media type:** {info.media_type}\n"
            f"- **Dimensions:** {info.width}×{info.height}\n"
            f"- **Mode:** {info.mode}\n"
            f"- **Size:** {info.size_bytes} bytes\n"
        )

    raise ValueError(f"Unsupported format: {output_format}")
