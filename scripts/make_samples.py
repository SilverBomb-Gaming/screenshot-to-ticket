"""Draw the synthetic FixtureApp screenshots under samples/.

These are portfolio fixtures: a made-up product, no third-party branding,
and no personal data. Re-run this script to regenerate the PNGs.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

BG = "#eef1f6"
CARD = "#ffffff"
INK = "#1f2937"
MUTED = "#6b7280"
LINE = "#d5dbe3"
INPUT_BG = "#f8fafc"
INPUT_BORDER = "#cbd5e1"
DANGER_BG = "#fef2f2"
DANGER_BORDER = "#f87171"
DANGER_INK = "#991b1b"
BUTTON = "#1d4ed8"
BAR = "#111827"
AMBER_BG = "#fff7ed"
AMBER_BORDER = "#fb923c"
AMBER_INK = "#9a3412"
DISABLED = "#e5e7eb"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.is_file():
        raise SystemExit(f"Missing font: {path}")
    return ImageFont.truetype(str(path), size=size)


def center_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    face: ImageFont.FreeTypeFont,
    fill: str,
) -> None:
    x0, y0, x1, y1 = box
    bbox = draw.textbbox((0, 0), text, font=face)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = x0 + (x1 - x0 - width) / 2
    y = y0 + (y1 - y0 - height) / 2 - bbox[1]
    draw.text((x, y), text, font=face, fill=fill)


def draw_login(path: Path) -> None:
    image = Image.new("RGB", (960, 600), BG)
    draw = ImageDraw.Draw(image)
    title = font(BOLD, 28)
    body = font(REGULAR, 16)
    small = font(REGULAR, 14)
    label = font(BOLD, 14)

    draw.rounded_rectangle((140, 36, 820, 564), radius=16, fill=CARD, outline=LINE, width=2)
    draw.text((180, 64), "FixtureApp", font=title, fill=INK)
    draw.text((180, 108), "Portfolio fixture — not a real product", font=small, fill=MUTED)

    draw.text((180, 156), "Email", font=label, fill=INK)
    draw.rounded_rectangle((180, 182, 780, 228), radius=8, fill=INPUT_BG, outline=INPUT_BORDER, width=2)
    draw.text((196, 194), "ada@example.test", font=body, fill=INK)

    draw.text((180, 248), "Password", font=label, fill=INK)
    draw.rounded_rectangle((180, 274, 780, 320), radius=8, fill=INPUT_BG, outline=INPUT_BORDER, width=2)
    draw.text((196, 286), "••••••••", font=body, fill=INK)

    draw.rounded_rectangle((180, 348, 780, 412), radius=8, fill=DANGER_BG, outline=DANGER_BORDER, width=2)
    draw.text((196, 368), "Sign-in failed. Check the email and password.", font=body, fill=DANGER_INK)

    draw.rounded_rectangle((180, 436, 780, 492), radius=8, fill=BUTTON)
    center_text(draw, (180, 436, 780, 492), "Sign in", font(BOLD, 16), "white")

    draw.text((180, 516), "No error code or stack trace is shown.", font=small, fill=MUTED)
    image.save(path, format="PNG", optimize=True)


def draw_checkout(path: Path) -> None:
    image = Image.new("RGB", (960, 640), BG)
    draw = ImageDraw.Draw(image)
    title = font(BOLD, 22)
    body = font(REGULAR, 16)
    small = font(REGULAR, 14)
    label = font(BOLD, 16)

    draw.rectangle((0, 0, 960, 64), fill=BAR)
    draw.text((32, 18), "FixtureApp", font=font(BOLD, 20), fill="white")
    draw.text((860, 20), "Cart", font=body, fill="#e5e7eb")

    draw.text((48, 88), "Your cart", font=font(BOLD, 26), fill=INK)
    draw.text((48, 128), "Portfolio fixture — not a real product", font=small, fill=MUTED)

    draw.rounded_rectangle((48, 176, 912, 280), radius=12, fill=CARD, outline=LINE, width=2)
    draw.text((72, 200), "Demo widget", font=title, fill=INK)
    draw.text((72, 234), "Qty 1", font=body, fill=MUTED)
    price = "$12.00"
    price_box = draw.textbbox((0, 0), price, font=label)
    price_w = price_box[2] - price_box[0]
    draw.text((880 - price_w, 214), price, font=label, fill=INK)

    draw.text((48, 312), "Total", font=label, fill=INK)
    draw.rounded_rectangle((720, 296, 912, 352), radius=8, fill=INPUT_BG, outline=INPUT_BORDER, width=2)
    center_text(draw, (720, 296, 912, 352), "—", font(BOLD, 22), MUTED)

    draw.rounded_rectangle((48, 384, 912, 456), radius=8, fill=AMBER_BG, outline=AMBER_BORDER, width=2)
    draw.text((68, 406), "We couldn't calculate the total.", font=body, fill=AMBER_INK)

    draw.rounded_rectangle((48, 488, 320, 544), radius=8, fill=DISABLED, outline=LINE, width=2)
    center_text(draw, (48, 488, 320, 544), "Place order", font(BOLD, 16), MUTED)

    draw.text(
        (48, 580),
        "Synthetic screen. No third-party branding. No error code is shown.",
        font=small,
        fill=MUTED,
    )
    image.save(path, format="PNG", optimize=True)


def main() -> None:
    SAMPLES.mkdir(exist_ok=True)
    login = SAMPLES / "login-error.png"
    checkout = SAMPLES / "checkout-total.png"
    draw_login(login)
    draw_checkout(checkout)
    for path in (login, checkout):
        print(f"wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
