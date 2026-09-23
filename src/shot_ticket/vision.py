"""Vision backends: local Ollama, or an opt-in OpenAI-compatible endpoint."""

from __future__ import annotations

import base64
from typing import Any, Protocol

import httpx

from shot_ticket.config import ConfigError, Settings
from shot_ticket.images import ImageInfo


class VisionError(RuntimeError):
    """The vision endpoint could not be reached or returned nothing usable."""


class VisionClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        image: ImageInfo,
        image_bytes: bytes,
    ) -> str:
        """Return the model's raw text reply."""


class OllamaVisionClient:
    """Talk to a local Ollama server via ``POST /api/chat``."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str | None,
        timeout: float,
        json_mode: bool,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.json_mode = json_mode
        self._http = http_client
        # Local Ollama does not need a bearer token. Never forward one.
        self.send_auth = False

    def complete(
        self,
        *,
        system: str,
        user: str,
        image: ImageInfo,
        image_bytes: bytes,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": user,
                    "images": [_b64(image_bytes)],
                },
            ],
            "options": {"temperature": 0},
        }
        if self.json_mode:
            payload["format"] = "json"
        data = _post_json(
            self,
            path="/api/chat",
            payload=payload,
            connect_hint=(
                f"Could not reach Ollama at {self.base_url}. "
                "Start it with `ollama serve` and pull the vision model with "
                f"`ollama pull {self.model}`."
            ),
        )
        message = data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        return _require_text(content)


class OpenAIVisionClient:
    """Talk to ``POST {base}/chat/completions`` with an image data URL.

    This is opt-in. The image leaves the machine when the base URL is not local.
    """

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str | None,
        timeout: float,
        json_mode: bool,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.json_mode = json_mode
        self._http = http_client
        self.send_auth = True

    def complete(
        self,
        *,
        system: str,
        user: str,
        image: ImageInfo,
        image_bytes: bytes,
    ) -> str:
        data_url = f"data:{image.media_type};base64,{_b64(image_bytes)}"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = _post_json(
            self,
            path="/chat/completions",
            payload=payload,
            connect_hint=(
                f"Could not reach the OpenAI-compatible endpoint at {self.base_url}."
            ),
        )
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise VisionError("OpenAI-compatible response had no choices.")
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        return _require_text(content)


def build_client(
    settings: Settings,
    *,
    http_client: httpx.Client | None = None,
) -> VisionClient:
    kwargs = {
        "model": settings.model,
        "base_url": settings.base_url,
        "api_key": settings.api_key,
        "timeout": settings.timeout,
        "json_mode": settings.json_mode,
        "http_client": http_client,
    }
    if settings.provider == "ollama":
        return OllamaVisionClient(**kwargs)
    if settings.provider == "openai":
        return OpenAIVisionClient(**kwargs)
    raise ConfigError("Provider must be 'ollama' or 'openai'.")


def _b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("ascii")


def _require_text(content: object) -> str:
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        joined = "".join(parts).strip()
        if joined:
            return joined
    raise VisionError("Vision response did not include text content.")


def _post_json(
    client: OllamaVisionClient | OpenAIVisionClient,
    *,
    path: str,
    payload: dict[str, Any],
    connect_hint: str,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if client.send_auth and client.api_key:
        headers["Authorization"] = f"Bearer {client.api_key}"

    owns_client = client._http is None
    http = client._http or httpx.Client(timeout=client.timeout, follow_redirects=True)
    try:
        try:
            response = http.post(
                f"{client.base_url}{path}",
                json=payload,
                headers=headers,
                timeout=client.timeout,
            )
        except httpx.ConnectError as exc:
            raise VisionError(connect_hint) from exc
        except httpx.TimeoutException as exc:
            raise VisionError(
                f"Vision request timed out after {client.timeout:g}s."
            ) from exc
    finally:
        if owns_client:
            http.close()

    if response.status_code >= 400:
        raise VisionError(
            f"Vision request failed ({response.status_code}): {_error_detail(response)}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise VisionError("Vision response was not JSON.") from exc
    if not isinstance(data, dict):
        raise VisionError("Vision response JSON must be an object.")
    return data


def _error_detail(response: httpx.Response) -> str:
    payload: object
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
    text = response.text.strip()
    if len(text) > 400:
        text = text[:400] + "..."
    return text or "no response body"
