from __future__ import annotations

import json

from backend.config import Settings
from backend.services import image_storage


class FakeResponse:
    def __init__(self, body: bytes = b""):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body


def supabase_settings(tmp_path):
    return Settings(
        supabase_url="https://project.supabase.co",
        supabase_service_role_key="server-only-test-key",
        supabase_storage_bucket="receipts",
        upload_dir=str(tmp_path),
    )


def test_upload_uses_private_supabase_storage_and_returns_object_key(monkeypatch, tmp_path):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(image_storage, "urlopen", fake_urlopen)
    settings = supabase_settings(tmp_path)

    key = image_storage.save_receipt_image(b"png-bytes", "abc123", settings)

    request = seen["request"]
    assert key == "abc123.png"
    assert request.get_method() == "POST"
    assert request.full_url.endswith("/storage/v1/object/receipts/abc123.png")
    assert request.get_header("X-upsert") == "true"
    assert request.get_header("Authorization") == "Bearer server-only-test-key"
    assert request.data == b"png-bytes"


def test_private_bucket_signed_url_is_returned_from_supabase(monkeypatch, tmp_path):
    monkeypatch.setattr(
        image_storage,
        "urlopen",
        lambda request, timeout: FakeResponse(
            json.dumps({"signedURL": "/object/sign/receipts/a.png?token=x"}).encode()
        ),
    )

    signed = image_storage.signed_receipt_image_url("a.png", supabase_settings(tmp_path))

    assert signed == "https://project.supabase.co/storage/v1/object/sign/receipts/a.png?token=x"


def test_supabase_delete_uses_bucket_object_prefix(monkeypatch, tmp_path):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"] = request
        return FakeResponse(b"{}")

    monkeypatch.setattr(image_storage, "urlopen", fake_urlopen)

    image_storage.delete_receipt_image("abc123.png", supabase_settings(tmp_path))

    request = seen["request"]
    assert request.get_method() == "DELETE"
    assert request.full_url.endswith("/storage/v1/object/receipts")
    assert json.loads(request.data) == {"prefixes": ["abc123.png"]}


def test_local_storage_still_saves_and_deletes_images(tmp_path):
    settings = Settings(upload_dir=str(tmp_path))

    path = image_storage.save_receipt_image(b"local-image", "hash", settings)
    image_storage.delete_receipt_image(path, settings)

    assert path.endswith("hash.png")
    assert not (tmp_path / "hash.png").exists()
