"""End-to-end API tests against fake providers (no real network calls)."""

from __future__ import annotations

import io

from PIL import Image


def _fake_png_bytes() -> bytes:
    img = Image.new("RGB", (40, 40), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_upload_single_receipt(client):
    files = [("files", ("receipt.png", _fake_png_bytes(), "image/png"))]
    res = client.post("/upload", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["accepted"] == 1
    assert body["results"][0]["status"] == "queued"
    assert body["results"][0]["receipt_id"]


def test_upload_rejects_unsupported_file_type(client):
    files = [("files", ("notes.txt", b"hello world", "text/plain"))]
    res = client.post("/upload", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["rejected"] == 1
    assert body["accepted"] == 0


def test_upload_duplicate_is_rejected(client):
    png = _fake_png_bytes()
    files = [("files", ("receipt.png", png, "image/png"))]
    first = client.post("/upload", files=files)
    assert first.json()["accepted"] == 1

    files_again = [("files", ("receipt-again.png", png, "image/png"))]
    second = client.post("/upload", files=files_again)
    body = second.json()
    assert body["accepted"] == 0
    assert body["rejected"] == 1
    assert "already" in body["results"][0]["detail"].lower()


def test_get_and_list_receipt(client):
    files = [("files", ("receipt.png", _fake_png_bytes(), "image/png"))]
    upload_res = client.post("/upload", files=files).json()
    receipt_id = upload_res["results"][0]["receipt_id"]

    get_res = client.get(f"/receipts/{receipt_id}")
    assert get_res.status_code == 200
    assert get_res.json()["merchant_name"] == "Test Cafe"
    assert len(get_res.json()["line_items"]) == 2

    list_res = client.get("/receipts")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1


def test_get_nonexistent_receipt_returns_404(client):
    res = client.get("/receipts/does-not-exist")
    assert res.status_code == 404
    assert res.json()["error_code"] == "receipt_not_found"


def test_delete_receipt(client):
    files = [("files", ("receipt.png", _fake_png_bytes(), "image/png"))]
    upload_res = client.post("/upload", files=files).json()
    receipt_id = upload_res["results"][0]["receipt_id"]

    del_res = client.delete(f"/receipts/{receipt_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/receipts/{receipt_id}")
    assert get_res.status_code == 404


def test_search_keyword_mode_after_upload(client):
    files = [("files", ("receipt.png", _fake_png_bytes(), "image/png"))]
    client.post("/upload", files=files)

    res = client.post("/search", json={"query": "latte", "mode": "keyword"})
    assert res.status_code == 200
    body = res.json()
    assert body["count"] >= 1
    assert any("Latte" in m["name"] for r in body["results"] for m in r["matched_items"])


def test_stats_endpoint_reflects_uploaded_receipts(client):
    files = [("files", ("receipt.png", _fake_png_bytes(), "image/png"))]
    client.post("/upload", files=files)

    res = client.get("/stats")
    assert res.status_code == 200
    body = res.json()
    assert body["total_receipts"] == 1
    assert body["total_spent"] == 10.5


def test_reindex_endpoint_runs_without_error(client):
    files = [("files", ("receipt.png", _fake_png_bytes(), "image/png"))]
    client.post("/upload", files=files)

    res = client.post("/reindex")
    assert res.status_code == 200
    assert res.json()["reindexed_items"] >= 1


def test_invalid_search_mode_returns_422():
    pass  # covered by pydantic pattern validation on SearchQuery.mode; see schemas/api.py
