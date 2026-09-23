"""HTTP clients, with MockTransport. No live Ollama or network."""

from __future__ import annotations

import base64
import json

import httpx
import pytest
from PIL import Image

from shot_ticket.config import resolve_settings
from shot_ticket.images import inspect_image
from shot_ticket.prompt import SYSTEM_PROMPT
from shot_ticket.vision import (
    OllamaVisionClient,
    OpenAIVisionClient,
    VisionError,
    build_client,
)
from tests.conftest import TICKET_JSON


def _png(tmp_path):
    path = tmp_path / "screen.png"
    Image.new("RGB", (4, 4), "blue").save(path, format="PNG")
    return path, inspect_image(path)


def _client(handler, cls, **kwargs):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    defaults = dict(
        model="llava",
        base_url="http://127.0.0.1:11434",
        api_key=None,
        timeout=5,
        json_mode=True,
        http_client=http,
    )
    defaults.update(kwargs)
    return cls(**defaults)


def test_ollama_posts_prompt_image_and_ignores_api_key(tmp_path):
    path, info = _png(tmp_path)
    raw = path.read_bytes()
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"message": {"content": TICKET_JSON}})

    client = _client(handler, OllamaVisionClient, api_key="should-not-be-sent")
    text = client.complete(system=SYSTEM_PROMPT, user="describe", image=info, image_bytes=raw)

    assert "Sign-in failed" in text
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert seen["auth"] is None
    body = seen["body"]
    assert body["model"] == "llava"
    assert body["stream"] is False
    assert body["format"] == "json"
    assert body["options"]["temperature"] == 0
    assert body["messages"][0]["content"] == SYSTEM_PROMPT
    assert "Do not invent UI text" in body["messages"][0]["content"]
    assert base64.b64decode(body["messages"][1]["images"][0]) == raw


def test_ollama_json_mode_can_be_disabled(tmp_path):
    path, info = _png(tmp_path)
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"message": {"content": TICKET_JSON}})

    client = _client(handler, OllamaVisionClient, json_mode=False)
    client.complete(system="sys", user="user", image=info, image_bytes=path.read_bytes())
    assert "format" not in seen["body"]


def test_ollama_error_and_connection_messages(tmp_path):
    path, info = _png(tmp_path)

    def missing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'llava' not found"})

    client = _client(missing, OllamaVisionClient)
    with pytest.raises(VisionError, match="llava"):
        client.complete(system="s", user="u", image=info, image_bytes=path.read_bytes())

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = _client(down, OllamaVisionClient, model="llava")
    with pytest.raises(VisionError, match="ollama pull llava"):
        client.complete(system="s", user="u", image=info, image_bytes=path.read_bytes())

    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    client = _client(slow, OllamaVisionClient, timeout=3)
    with pytest.raises(VisionError, match="timed out after 3s"):
        client.complete(system="s", user="u", image=info, image_bytes=path.read_bytes())


def test_openai_payload_shape(tmp_path):
    path, info = _png(tmp_path)
    raw = path.read_bytes()
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": TICKET_JSON}}]},
        )

    client = _client(
        handler,
        OpenAIVisionClient,
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
    )
    text = client.complete(system=SYSTEM_PROMPT, user="look", image=info, image_bytes=raw)
    assert text == TICKET_JSON
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    body = seen["body"]
    assert body["model"] == "gpt-4o"
    assert body["response_format"] == {"type": "json_object"}
    assert body["messages"][0]["content"] == SYSTEM_PROMPT
    parts = body["messages"][1]["content"]
    assert parts[0]["type"] == "text"
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
    encoded = parts[1]["image_url"]["url"].split(",", 1)[1]
    assert base64.b64decode(encoded) == raw
    assert "temperature" not in body


def test_openai_optional_key_json_mode_and_list_content(tmp_path):
    path, info = _png(tmp_path)
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": [{"type": "text", "text": TICKET_JSON}]}}]},
        )

    client = _client(
        handler,
        OpenAIVisionClient,
        model="local-vision",
        base_url="http://127.0.0.1:8080/v1/",
        api_key=None,
        json_mode=False,
    )
    text = client.complete(system="s", user="u", image=info, image_bytes=path.read_bytes())
    assert text == TICKET_JSON
    assert seen["auth"] is None
    assert "response_format" not in seen["body"]
    assert seen["body"]["messages"][0]["content"] == "s"


def test_empty_content_is_an_error(tmp_path):
    path, info = _png(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "  "}})

    client = _client(handler, OllamaVisionClient)
    with pytest.raises(VisionError, match="did not include text"):
        client.complete(system="s", user="u", image=info, image_bytes=path.read_bytes())


def test_openai_error_object_message(tmp_path):
    path, info = _png(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "model not found"}})

    client = _client(handler, OpenAIVisionClient, model="missing")
    with pytest.raises(VisionError, match="model not found"):
        client.complete(system="s", user="u", image=info, image_bytes=path.read_bytes())


def test_build_client_selects_backend():
    ollama = build_client(resolve_settings(env={}))
    openai = build_client(resolve_settings(provider="openai", model="gpt-4o", env={}))
    assert isinstance(ollama, OllamaVisionClient)
    assert isinstance(openai, OpenAIVisionClient)
    assert openai.base_url == "https://api.openai.com/v1"
