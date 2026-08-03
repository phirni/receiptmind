"""Application-level exceptions, mapped to HTTP responses in api/main.py."""

from __future__ import annotations


class ReceiptMindError(Exception):
    """Base class for all expected application errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsupportedFileTypeError(ReceiptMindError):
    status_code = 415
    error_code = "unsupported_file_type"


class FileTooLargeError(ReceiptMindError):
    status_code = 413
    error_code = "file_too_large"


class DuplicateReceiptError(ReceiptMindError):
    status_code = 409
    error_code = "duplicate_receipt"


class ExtractionFailedError(ReceiptMindError):
    status_code = 422
    error_code = "extraction_failed"


class ReceiptNotFoundError(ReceiptMindError):
    status_code = 404
    error_code = "receipt_not_found"


class InvalidSearchQueryError(ReceiptMindError):
    status_code = 400
    error_code = "invalid_search_query"
