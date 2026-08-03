"""Provider factory — the single place that knows concrete provider classes."""

from __future__ import annotations

from functools import lru_cache

from backend.config import Settings
from backend.providers.base import VisionProvider, VisionProviderError


@lru_cache
def _build(provider: str, api_key: str, model: str, timeout_seconds: int, max_retries: int) -> VisionProvider:
    if provider == "gemini":
        from backend.providers.gemini_provider import GeminiProvider

        return GeminiProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    # Future providers register here:
    # if provider == "groq": from backend.providers.groq_provider import GroqProvider; ...
    # if provider == "openrouter": ...
    # if provider == "glm": ...
    if provider == "openrouter":
        from backend.providers.openrouter_provider import OpenRouterProvider

        return OpenRouterProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    raise VisionProviderError(f"Unknown VISION_PROVIDER: {provider!r}")


def get_vision_provider(settings: Settings) -> VisionProvider:
    provider = settings.vision_provider.lower()

    if provider == "gemini":
        api_key = settings.gemini_api_key
        model = settings.gemini_vision_model

    elif provider == "openrouter":
        api_key = settings.openrouter_api_key
        model = settings.openrouter_model

    else:
        raise VisionProviderError(f"Unknown VISION_PROVIDER: {provider!r}")

    return _build(
        provider,
        api_key,
        model,
        settings.extraction_timeout_seconds,
        settings.extraction_max_retries,
    )