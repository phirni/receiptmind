"""Upload validation and format normalization.

Receipts can arrive as jpg/jpeg/png/webp or pdf. Everything is normalized to
a single PNG image (first page only, for multi-page PDFs) before it's sent to
the vision provider, so `providers/` only ever has to deal with one format.
"""

from __future__ import annotations

import hashlib
import io

from PIL import Image

from backend.utils.exceptions import UnsupportedFileTypeError

_SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_PDF_TYPE = "application/pdf"


def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_to_png(data: bytes, content_type: str, filename: str) -> bytes:
    """Return PNG bytes for any supported input, or raise UnsupportedFileTypeError."""
    content_type = (content_type or "").lower()

    if content_type == _PDF_TYPE or filename.lower().endswith(".pdf"):
        return _first_pdf_page_to_png(data)

    if content_type in _SUPPORTED_IMAGE_TYPES or filename.lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp")
    ):
        return _image_to_png(data)

    raise UnsupportedFileTypeError(
        f"Unsupported file type '{content_type or filename}'. " "Allowed: jpg, jpeg, png, webp, pdf."
    )


def _image_to_png(data: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(data)) as img:
            rgb_img = img.convert("RGB")
            buf = io.BytesIO()
            rgb_img.save(buf, format="PNG")
            return buf.getvalue()
    except Exception as exc:  # noqa: BLE001
        raise UnsupportedFileTypeError(f"Could not decode image: {exc}") from exc


def _first_pdf_page_to_png(data: bytes) -> bytes:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover
        raise UnsupportedFileTypeError("PDF support requires PyMuPDF (pymupdf).") from exc

    try:
        doc = fitz.open(stream=data, filetype="pdf")
        try:
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=200)
            return pix.tobytes("png")
        finally:
            doc.close()
    except Exception as exc:  # noqa: BLE001
        raise UnsupportedFileTypeError(f"Could not render PDF: {exc}") from exc
