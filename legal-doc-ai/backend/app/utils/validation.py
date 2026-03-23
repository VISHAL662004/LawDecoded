from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings


async def validate_pdf_upload(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    content = await file.read()
    await file.seek(0)

    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_size_mb} MB limit",
        )

    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF binary")
