from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.schemas.analysis import HealthResponse
from app.utils.device import get_torch_device

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name, device=get_torch_device())
