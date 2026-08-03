"""Gemini 2.5 Flash implementation of VisionProvider.

Uses the free-tier-eligible `gemini-2.5-flash` model via the `google-genai`
SDK, with `response_schema` to force strict JSON matching `ExtractedReceipt`.
"""

from __future__ import annotations

import asyncio
import json
import logging

from google import genai
from google.genai import types
from pydantic import ValidationError

from backend.providers.base import VisionProvider, VisionProviderError
from backend.schemas.extraction import EXTRACTION_JSON_SCHEMA, ExtractedReceipt

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """You are a precise receipt-reading system.

Read the attached receipt image and extract every field you can determine
with confidence. Follow these rules strictly:

- Output ONLY JSON matching the provided schema. No prose, no markdown fences.
- If a field is not present on the receipt, omit it (do not invent values).
- `total` is required; if illegible, use your best estimate and lower `confidence`.
- Every purchased item goes in `line_items`, one entry per line, preserving
  the merchant's own item names verbatim (don't normalize brand names away).
- `category` should be a short general grocery/retail category
  (e.g. "beverages", "produce", "snacks", "electronics", "dining"), lowercase.
- `purchase_datetime` should be ISO-8601 if a date (and time, if shown) is visible.
- Set `confidence` in [0, 1] reflecting how legible/complete the receipt was.
"""


class GeminiProvider(VisionProvider):
    def __init__(self, api_key: str, model: str, timeout_seconds: int, max_retries: int) -> None:
        if not api_key:
            raise VisionProviderError("GEMINI_API_KEY is not configured.")
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    async def extract_receipt(self, image_bytes: bytes, mime_type: str) -> ExtractedReceipt:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                raw_text = await asyncio.wait_for(
                    self._call_model(image_bytes, mime_type), timeout=self._timeout
                )
                return self._parse(raw_text)
            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning("Extraction attempt %d produced invalid JSON: %s", attempt + 1, exc)
            except TimeoutError as exc:
                last_error = exc
                logger.warning("Extraction attempt %d timed out", attempt + 1)
            except Exception as exc:  # noqa: BLE001 - normalize all provider errors
                last_error = exc
                logger.warning("Extraction attempt %d failed: %s", attempt + 1, exc)
            await asyncio.sleep(min(2**attempt, 8))
        raise VisionProviderError(f"Gemini extraction failed after retries: {last_error}") from last_error

    async def _call_model(self, image_bytes: bytes, mime_type: str) -> str:
        def _sync_call() -> str:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    _EXTRACTION_PROMPT,
                ],  # type: ignore[arg-type]
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedReceipt,
                    temperature=0.1,
                ),
            )
            return response.text or ""

        return await asyncio.to_thread(_sync_call)

    @staticmethod
    def _parse(raw_text: str) -> ExtractedReceipt:
        data = json.loads(raw_text)
        return ExtractedReceipt.model_validate(data)
