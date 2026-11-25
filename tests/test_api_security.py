import io

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

import config
from api import main, security


def _upload(data: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename="p.pdf")


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "s3cret")
    return "s3cret"


def test_require_api_key_accepts_matching_key(api_key):
    assert security.require_api_key("s3cret") is None


@pytest.mark.parametrize("sent", ["", "wrong", "s3cret ", "S3CRET"])
def test_require_api_key_rejects_missing_or_wrong_key(api_key, sent):
    with pytest.raises(HTTPException) as exc:
        security.require_api_key(sent)
    assert exc.value.status_code == 401


def test_require_api_key_fails_closed_when_no_key_is_configured(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "")
    with pytest.raises(HTTPException) as exc:
        security.require_api_key("")
    assert exc.value.status_code == 401


@pytest.mark.parametrize(
    "method, path",
    [
        ("post", "/analyze"),
        ("post", "/analyze/stream"),
        ("post", "/resume"),
        ("get", "/state/abc"),
        ("post", "/ingest"),
        ("post", "/chat"),
    ],
)
def test_every_business_endpoint_requires_the_key(api_key, method, path):
    client = TestClient(main.app)
    assert getattr(client, method)(path).status_code == 401
    assert getattr(client, method)(path, headers={"X-API-Key": "wrong"}).status_code == 401


def test_startup_refuses_to_run_without_an_api_key(monkeypatch):
    import asyncio

    monkeypatch.setattr(config, "validate_required", lambda: None)
    monkeypatch.setattr(config, "API_KEY", "")

    async def start():
        async with main.lifespan(main.app):
            pass

    with pytest.raises(RuntimeError, match="REGWATCH_API_KEY"):
        asyncio.run(start())


def test_read_pdf_upload_accepts_a_pdf():
    import asyncio

    data = b"%PDF-1.7 body"
    assert asyncio.run(security.read_pdf_upload(_upload(data))) == data


def test_read_pdf_upload_rejects_non_pdf_with_415():
    import asyncio

    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.read_pdf_upload(_upload(b"MZ\x90\x00 not a pdf")))
    assert exc.value.status_code == 415


def test_read_pdf_upload_rejects_oversized_with_413(monkeypatch):
    import asyncio

    monkeypatch.setattr(security, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.read_pdf_upload(_upload(b"%PDF-" + b"x" * 20)))
    assert exc.value.status_code == 413
