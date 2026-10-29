"""Receipt image persistence for local development and Supabase Storage."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from backend.config import Settings


def _object_url(settings: Settings, key: str) -> str:
    bucket = quote(settings.supabase_storage_bucket, safe="")
    object_key = quote(key, safe="/")
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{object_key}"


def _storage_request(settings: Settings, request: Request) -> bytes:
    request.add_header("Authorization", f"Bearer {settings.supabase_service_role_key}")
    request.add_header("apikey", settings.supabase_service_role_key)
    try:
        with urlopen(request, timeout=20) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("Supabase Storage request failed") from exc


def save_receipt_image(png_bytes: bytes, image_hash: str, settings: Settings) -> str:
    """Save the normalized receipt and return a local path or storage object key."""
    if settings.supabase_storage_enabled:
        key = f"{image_hash}.png"
        request = Request(
            _object_url(settings, key),
            data=png_bytes,
            headers={"Content-Type": "image/png", "x-upsert": "true"},
            method="POST",
        )
        _storage_request(settings, request)
        return key

    path = Path(settings.upload_dir) / f"{image_hash}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(png_bytes)
    return str(path)


def delete_receipt_image(image_path: str, settings: Settings) -> None:
    if settings.supabase_storage_enabled:
        bucket = quote(settings.supabase_storage_bucket, safe="")
        url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}"
        request = Request(
            url,
            data=json.dumps({"prefixes": [image_path]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="DELETE",
        )
        _storage_request(settings, request)
        return

    Path(image_path).unlink(missing_ok=True)


def signed_receipt_image_url(image_path: str, settings: Settings, expires_in: int = 3600) -> str:
    bucket = quote(settings.supabase_storage_bucket, safe="")
    object_key = quote(image_path, safe="/")
    endpoint = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/sign/{bucket}/{object_key}"
    request = Request(
        endpoint,
        data=json.dumps({"expiresIn": expires_in}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    response = json.loads(_storage_request(settings, request))
    signed_path = response.get("signedURL") or response.get("signedUrl")
    if not signed_path:
        raise RuntimeError("Supabase Storage did not return a signed image URL")
    if signed_path.startswith("http://") or signed_path.startswith("https://"):
        return signed_path
    if not signed_path.startswith("/"):
        signed_path = f"/{signed_path}"
    return f"{settings.supabase_url.rstrip('/')}/storage/v1{signed_path}"
