"""CLI behavior, including dry-run with no model client."""

from __future__ import annotations

import json

import pytest

from shot_ticket.cli import main, run
from shot_ticket.prompt import SYSTEM_PROMPT
from shot_ticket.vision import VisionError
from tests.conftest import TICKET, FakeVision, TICKET_JSON


def test_dry_run_prints_metadata_and_does_not_build_a_client(login_png, monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise AssertionError("dry-run must not build a vision client")

    monkeypatch.setattr("shot_ticket.cli.build_client", boom)
    code = run(["draft", "--image", str(login_png), "--dry-run"])
    captured = capsys.readouterr()
    assert code == 0
    assert "No model was called." in captured.out
    assert "960×600" in captured.out
    assert captured.err == ""


def test_dry_run_json(checkout_png, capsys):
    code = run(["draft", "--image", str(checkout_png), "--dry-run", "--format", "json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["model_called"] is False
    assert payload["width"] == 960
    assert payload["height"] == 640
    assert payload["format"] == "PNG"


def test_draft_markdown_uses_injected_client(login_png, monkeypatch, capsys):
    fake = FakeVision(TICKET_JSON)

    def factory(settings, http_client=None):
        assert settings.model == "llava"
        return fake

    monkeypatch.setattr("shot_ticket.cli.build_client", factory)
    code = run(["draft", "--image", str(login_png)])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.startswith("# Sign-in failed on FixtureApp")
    assert "shot-ticket did not file this anywhere" in captured.out
    assert fake.calls[0]["system"] == SYSTEM_PROMPT
    assert "login-error" not in str(fake.calls[0]["user"])
    assert captured.err == ""


def test_draft_json_and_model_flag(login_png, monkeypatch, capsys):
    fake = FakeVision(TICKET_JSON)
    seen = {}

    def factory(settings, http_client=None):
        seen["model"] = settings.model
        seen["provider"] = settings.provider
        return fake

    monkeypatch.setattr("shot_ticket.cli.build_client", factory)
    code = run(
        [
            "draft",
            "--image",
            str(login_png),
            "--format",
            "json",
            "--model",
            "llama3.2-vision",
            "--provider",
            "ollama",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["title"] == TICKET["title"]
    assert payload["screenshot"]["filename"] == "login-error.png"
    assert seen == {"model": "llama3.2-vision", "provider": "ollama"}


def test_out_writes_a_file_and_leaves_stdout_empty(login_png, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        "shot_ticket.cli.build_client",
        lambda settings, http_client=None: FakeVision(TICKET_JSON),
    )
    dest = tmp_path / "ticket.md"
    code = run(["draft", "--image", str(login_png), "--out", str(dest)])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == ""
    assert f"wrote {dest}" in captured.err
    assert dest.read_text(encoding="utf-8").startswith("# Sign-in failed")


def test_dry_run_can_write_metadata(login_png, capsys, tmp_path):
    dest = tmp_path / "meta.json"
    code = run(
        ["draft", "--image", str(login_png), "--dry-run", "--format", "json", "--out", str(dest)]
    )
    assert code == 0
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["model_called"] is False
    assert "wrote" in capsys.readouterr().err


def test_missing_image_exits_2_without_a_provider(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        "shot_ticket.cli.build_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("client built")),
    )
    code = run(
        ["draft", "--image", str(tmp_path / "missing.png"), "--provider", "openai"]
    )
    assert code == 2
    assert "not found" in capsys.readouterr().err


def test_bad_output_path_exits_2(login_png, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        "shot_ticket.cli.build_client",
        lambda settings, http_client=None: FakeVision(TICKET_JSON),
    )
    code = run(["draft", "--image", str(login_png), "--out", str(tmp_path / "nope" / "ticket.md")])
    assert code == 2
    assert "does not exist" in capsys.readouterr().err


def test_vision_and_parse_errors_exit_1(login_png, monkeypatch, capsys):
    class Down:
        def complete(self, **kwargs):
            raise VisionError("ollama is not running")

    monkeypatch.setattr("shot_ticket.cli.build_client", lambda settings, http_client=None: Down())
    assert run(["draft", "--image", str(login_png)]) == 1
    assert "ollama is not running" in capsys.readouterr().err

    monkeypatch.setattr(
        "shot_ticket.cli.build_client",
        lambda settings, http_client=None: FakeVision("not a ticket"),
    )
    assert run(["draft", "--image", str(login_png)]) == 1
    assert "JSON" in capsys.readouterr().err


def test_openai_without_a_model_exits_1(login_png, monkeypatch, capsys):
    for name in (
        "SHOT_TICKET_MODEL",
        "SHOT_TICKET_PROVIDER",
        "SHOT_TICKET_BASE_URL",
        "SHOT_TICKET_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    def boom(*args, **kwargs):
        raise AssertionError("client should not be built without a model")

    monkeypatch.setattr("shot_ticket.cli.build_client", boom)
    code = run(["draft", "--image", str(login_png), "--provider", "openai"])
    assert code == 1
    assert "SHOT_TICKET_MODEL" in capsys.readouterr().err


def test_main_exits_with_the_status_code(login_png):
    with pytest.raises(SystemExit) as exc:
        main(["draft", "--image", str(login_png), "--dry-run"])
    assert exc.value.code == 0


def test_out_directory_exits_2(login_png, capsys, tmp_path):
    code = run(["draft", "--image", str(login_png), "--dry-run", "--out", str(tmp_path)])
    assert code == 2
    assert "directory" in capsys.readouterr().err


def test_version_exits_0():
    with pytest.raises(SystemExit) as exc:
        run(["--version"])
    assert exc.value.code == 0


def test_both_samples_dry_run(login_png, checkout_png, capsys):
    assert run(["draft", "--image", str(login_png), "--dry-run"]) == 0
    assert run(["draft", "--image", str(checkout_png), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert out.count("No model was called.") == 2
