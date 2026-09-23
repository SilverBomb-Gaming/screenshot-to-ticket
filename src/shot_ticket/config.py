"""Resolve provider settings from flags and the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

DEFAULT_OLLAMA_MODEL = "llava"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 180.0

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


class ConfigError(ValueError):
    """Flags or environment variables are incomplete or contradictory."""


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    base_url: str
    api_key: str | None
    timeout: float
    json_mode: bool


def resolve_settings(
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Settings:
    """CLI values win over environment variables, which win over defaults.

    ``SHOT_TICKET_API_KEY`` is read only from the environment so the key does
    not need to appear in a process listing as a command-line argument.
    """
    source = os.environ if env is None else env

    chosen_provider = _first(provider, source.get("SHOT_TICKET_PROVIDER"), "ollama").lower()
    if chosen_provider not in {"ollama", "openai"}:
        raise ConfigError("Provider must be 'ollama' or 'openai'.")

    chosen_model = _first(model, source.get("SHOT_TICKET_MODEL"), "")
    if not chosen_model:
        if chosen_provider == "ollama":
            chosen_model = DEFAULT_OLLAMA_MODEL
        else:
            raise ConfigError(
                "Set SHOT_TICKET_MODEL or pass --model when the provider is openai."
            )

    chosen_base = _first(base_url, source.get("SHOT_TICKET_BASE_URL"), "")
    if not chosen_base:
        chosen_base = (
            DEFAULT_OLLAMA_BASE_URL
            if chosen_provider == "ollama"
            else DEFAULT_OPENAI_BASE_URL
        )
    chosen_base = chosen_base.rstrip("/")

    api_key = source.get("SHOT_TICKET_API_KEY", "").strip() or None
    timeout = _timeout(source.get("SHOT_TICKET_TIMEOUT"))
    json_mode = _bool_flag(source.get("SHOT_TICKET_JSON_MODE"), default=True)

    return Settings(
        provider=chosen_provider,
        model=chosen_model,
        base_url=chosen_base,
        api_key=api_key,
        timeout=timeout,
        json_mode=json_mode,
    )


def _first(*values: str | None) -> str:
    for value in values:
        if value is None:
            continue
        stripped = value.strip()
        if stripped:
            return stripped
    return ""


def _timeout(raw: str | None) -> float:
    text = DEFAULT_TIMEOUT_SECONDS if raw is None or raw.strip() == "" else raw.strip()
    try:
        timeout = float(text)
    except ValueError as exc:
        raise ConfigError("SHOT_TICKET_TIMEOUT must be a number of seconds.") from exc
    if timeout <= 0:
        raise ConfigError("SHOT_TICKET_TIMEOUT must be positive.")
    return timeout


def _bool_flag(raw: str | None, *, default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in _TRUE:
        return True
    if normalized in _FALSE:
        return False
    raise ConfigError("SHOT_TICKET_JSON_MODE must be true or false.")
