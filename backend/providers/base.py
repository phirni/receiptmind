"""Vision provider abstraction.

Swapping the multimodal model that reads receipts should require editing only
`config.py` (VISION_PROVIDER) plus, if the new provider needs different
credentials, `.env`. No other module should import a concrete provider
class directly — always go through `providers.factory.get_vision_provider`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.schemas.extraction import ExtractedReceipt


class VisionProviderError(Exception):
    """Raised when a provider fails to produce a usable extraction."""


class VisionProvider(ABC):
    """Contract every multimodal receipt-extraction backend must satisfy."""

    @abstractmethod
    async def extract_receipt(self, image_bytes: bytes, mime_type: str) -> ExtractedReceipt:
        """Extract structured receipt data from a single image.

        Implementations must raise `VisionProviderError` on any failure
        (network, rate limit, malformed response) rather than letting
        provider-specific exceptions leak into the rest of the app.
        """
        raise NotImplementedError
