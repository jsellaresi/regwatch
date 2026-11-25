import hmac
import os

from fastapi import Header, HTTPException, UploadFile

import config

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
PDF_MAGIC = b"%PDF-"


def require_api_key(x_api_key: str = Header(default="")) -> None:
    expected = config.API_KEY
    if not expected or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def read_pdf_upload(file: UploadFile) -> bytes:
    """Read an upload, rejecting oversized or non-PDF files before fitz sees them."""
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")
    if not data.startswith(PDF_MAGIC):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted")
    return data
