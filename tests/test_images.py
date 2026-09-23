"""Image validation: type, content, and dry-run metadata."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from shot_ticket.images import MAX_IMAGE_BYTES, ImageError, inspect_image, render_metadata


def test_sample_login_is_png(login_png):
    info = inspect_image(login_png)
    assert info.format == "PNG"
    assert info.media_type == "image/png"
    assert (info.width, info.height) == (960, 600)
    assert info.size_bytes > 0


def test_sample_checkout_is_png(checkout_png):
    info = inspect_image(checkout_png)
    assert info.format == "PNG"
    assert (info.width, info.height) == (960, 640)


def test_missing_file(tmp_path):
    with pytest.raises(ImageError, match="not found"):
        inspect_image(tmp_path / "missing.png")


def test_directory_is_rejected(tmp_path):
    with pytest.raises(ImageError, match="not a file"):
        inspect_image(tmp_path)


def test_pdf_extension_is_rejected(tmp_path):
    path = tmp_path / "notes.pdf"
    path.write_bytes(b"%PDF-1.4")
    with pytest.raises(ImageError, match="Unsupported image type"):
        inspect_image(path)


def test_gif_extension_is_rejected(tmp_path):
    path = tmp_path / "anim.gif"
    Image.new("RGB", (8, 8), "red").save(path, format="GIF")
    with pytest.raises(ImageError, match="Unsupported image type"):
        inspect_image(path)


def test_png_extension_with_gif_content_is_rejected(tmp_path):
    path = tmp_path / "mislabeled.png"
    Image.new("RGB", (8, 8), "red").save(path, format="GIF")
    with pytest.raises(ImageError, match="does not match"):
        inspect_image(path)


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "empty.png"
    path.write_bytes(b"")
    with pytest.raises(ImageError, match="empty"):
        inspect_image(path)


def test_oversize_file_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("shot_ticket.images.MAX_IMAGE_BYTES", 8)
    path = tmp_path / "big.png"
    path.write_bytes(b"0123456789")
    with pytest.raises(ImageError, match="over the limit"):
        inspect_image(path)
    assert MAX_IMAGE_BYTES == 15 * 1024 * 1024


def test_jpeg_and_webp_are_accepted(tmp_path):
    jpeg = tmp_path / "shot.jpg"
    jpeg_ext = tmp_path / "shot.jpeg"
    webp = tmp_path / "shot.webp"
    Image.new("RGB", (12, 9), "blue").save(jpeg, format="JPEG")
    Image.new("RGB", (12, 9), "blue").save(jpeg_ext, format="JPEG")
    Image.new("RGB", (12, 9), "green").save(webp, format="WEBP")

    jpeg_info = inspect_image(jpeg)
    assert jpeg_info.format == "JPEG"
    assert jpeg_info.media_type == "image/jpeg"
    assert (jpeg_info.width, jpeg_info.height) == (12, 9)

    assert inspect_image(jpeg_ext).format == "JPEG"
    webp_info = inspect_image(webp)
    assert webp_info.format == "WEBP"
    assert webp_info.media_type == "image/webp"


def test_dry_run_metadata_formats(login_png):
    info = inspect_image(login_png)
    markdown = render_metadata(info, "markdown")
    assert "No model was called." in markdown
    assert "PNG" in markdown
    assert "960×600" in markdown

    payload = json.loads(render_metadata(info, "json"))
    assert payload["dry_run"] is True
    assert payload["model_called"] is False
    assert payload["format"] == "PNG"
    assert payload["width"] == 960
    assert payload["height"] == 600
    assert "title" not in payload
