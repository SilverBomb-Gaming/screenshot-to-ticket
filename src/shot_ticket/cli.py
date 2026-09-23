"""Command-line interface for shot-ticket."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence, TextIO

from shot_ticket import __version__
from shot_ticket.config import ConfigError, resolve_settings
from shot_ticket.draft import draft_from_info
from shot_ticket.images import ImageError, inspect_image, render_metadata
from shot_ticket.ticket import TicketParseError, render_ticket
from shot_ticket.vision import VisionError, build_client


class UsageError(ValueError):
    """The command line asked for something the tool will not do."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shot-ticket",
        description=(
            "Draft a structured bug ticket from a screenshot. "
            "The default model path is a local Ollama vision model. "
            "Nothing is posted to an issue tracker."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  shot-ticket draft --image samples/login-error.png --dry-run\n"
            "  shot-ticket draft --image samples/login-error.png --out ticket.md\n"
            "  shot-ticket draft --image samples/checkout-total.png --format json\n"
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    draft = sub.add_parser(
        "draft",
        help="Draft a ticket from a screenshot",
        description=(
            "Read a PNG, JPEG, or WebP screenshot and write a markdown or JSON ticket draft. "
            "Use --dry-run to validate the image and print metadata without calling a model."
        ),
    )
    draft.add_argument("--image", required=True, metavar="PATH", help="PNG, JPEG, or WebP screenshot")
    draft.add_argument("--out", metavar="PATH", help="Write the draft to this file instead of stdout")
    draft.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown)",
    )
    draft.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the image and print metadata; do not call a model",
    )
    draft.add_argument("--model", help="Vision model name (overrides SHOT_TICKET_MODEL)")
    draft.add_argument(
        "--provider",
        choices=("ollama", "openai"),
        help="ollama (default) or an OpenAI-compatible vision endpoint",
    )
    draft.add_argument("--base-url", help="Override the provider base URL")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return _draft(args)
    except (ImageError, UsageError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ConfigError, VisionError, TicketParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> None:
    sys.exit(run(argv))


def _draft(args: argparse.Namespace) -> int:
    info = inspect_image(Path(args.image))
    if args.dry_run:
        text = render_metadata(info, args.format)
    else:
        settings = resolve_settings(
            provider=args.provider,
            model=args.model,
            base_url=args.base_url,
        )
        client = build_client(settings)
        ticket = draft_from_info(info, client)
        text = render_ticket(ticket, info, args.format)

    _emit(text, Path(args.out) if args.out else None)
    return 0


def _emit(text: str, out: Path | None, *, stderr: TextIO | None = None) -> None:
    if out is None:
        sys.stdout.write(text)
        return
    if out.exists() and out.is_dir():
        raise UsageError(f"Output path is a directory: {out}")
    if not out.parent.exists():
        raise UsageError(f"Output directory does not exist: {out.parent}")
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}", file=stderr or sys.stderr)
