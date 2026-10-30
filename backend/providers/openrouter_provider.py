from __future__ import annotations

import asyncio
import base64
import json
import logging

from openai import OpenAI
from pydantic import ValidationError

from backend.providers.base import VisionProvider, VisionProviderError
from backend.schemas.extraction import ExtractedReceipt

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """You are a precise receipt-reading system.

Read the attached receipt image and extract every field you can determine
with confidence.

Return ONLY valid JSON matching this schema:

{
  "merchant_name": string,
  "merchant_address": string | null,
  "receipt_number": string | null,
  "currency": string,
  "subtotal": number | null,
  "tax": number | null,
  "total": number,
  "payment_method": string | null,
  "purchase_datetime": string | null,
  "confidence": number,
  "line_items": [
    {
      "name": string,
      "quantity": number,
      "unit_price": number | null,
      "total_price": number,
      "category": string | null
    }
  ]
}

Return ONLY JSON.
"""


class OpenRouterProvider(VisionProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> None:
        if not api_key:
            raise VisionProviderError("OPENROUTER_API_KEY is not configured.")
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    async def extract_receipt(
        self,
        image_bytes: bytes,
        mime_type: str,
    ) -> ExtractedReceipt:

        last_error = None

        for attempt in range(self._max_retries + 1):
            try:
                raw = await asyncio.wait_for(
                    self._call_model(image_bytes, mime_type),
                    timeout=self._timeout,
                )

                return self._parse(raw)

            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "Extraction attempt %d produced invalid JSON: %s",
                    attempt + 1,
                    exc,
                )

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Extraction attempt %d failed: %s",
                    attempt + 1,
                    exc,
                )

            await asyncio.sleep(min(2**attempt, 8))

        raise VisionProviderError(
            f"OpenRouter extraction failed after retries: {last_error}"
        )

    async def _call_model(
        self,
        image_bytes: bytes,
        mime_type: str,
    ) -> str:

        def _sync():

            image_b64 = base64.b64encode(image_bytes).decode()

            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": _EXTRACTION_PROMPT,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_b64}"
                                },
                            },
                        ],
                    }
                ],
            )

            return completion.choices[0].message.content

        return await asyncio.to_thread(_sync)

    @staticmethod
    def _parse(raw_text: str) -> ExtractedReceipt:
        data = json.loads(raw_text)
        return ExtractedReceipt.model_validate(data)
