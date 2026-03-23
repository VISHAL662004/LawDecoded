from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.analysis import AnalysisResult, JobStatus


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobStatus] = {}
        self._lock = asyncio.Lock()

    async def create(self) -> JobStatus:
        now = datetime.now(timezone.utc)
        job = JobStatus(
            job_id=str(uuid4()),
            status="queued",
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._jobs[job.job_id] = job
        return job

    async def get(self, job_id: str) -> JobStatus | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def mark_running(self, job_id: str) -> None:
        await self._update(job_id, status="running")

    async def mark_completed(self, job_id: str, result: AnalysisResult) -> None:
        await self._update(job_id, status="completed", result=result)

    async def mark_failed(self, job_id: str, error: str) -> None:
        await self._update(job_id, status="failed", error=error)

    async def _update(self, job_id: str, **kwargs: object) -> None:
        async with self._lock:
            item = self._jobs.get(job_id)
            if not item:
                return
            payload = item.model_dump()
            payload.update(kwargs)
            payload["updated_at"] = datetime.now(timezone.utc)
            self._jobs[job_id] = JobStatus(**payload)


job_store = InMemoryJobStore()
