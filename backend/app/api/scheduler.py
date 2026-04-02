"""
스케줄러 API 라우터.
크롤링 스케줄의 CRUD 엔드포인트를 제공한다.
스케줄 정보는 In-Memory 캐시에 JSON으로 저장한다.
"""

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import InMemoryCache, get_cache
from app.schemas.search import ScheduleJobRequest

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])

# 캐시에서 스케줄을 저장할 키 접두사
_SCHEDULE_KEY_PREFIX = "schedule:job:"
# 전체 스케줄 ID 목록을 관리하는 Set 키
_SCHEDULE_INDEX_KEY = "schedule:jobs"


@router.get("/jobs")
async def list_schedule_jobs(
    cache: InMemoryCache = Depends(get_cache),
) -> list[dict]:
    """등록된 모든 스케줄 목록을 반환한다."""

    # 스케줄 ID 목록 조회
    job_ids = await cache.smembers(_SCHEDULE_INDEX_KEY)
    jobs = []
    for job_id in sorted(job_ids):
        raw = await cache.get(f"{_SCHEDULE_KEY_PREFIX}{job_id}")
        if raw:
            jobs.append(json.loads(raw))
    return jobs


@router.post("/jobs")
async def create_schedule_job(
    request: ScheduleJobRequest,
    cache: InMemoryCache = Depends(get_cache),
) -> dict:
    """새 스케줄 작업을 등록한다."""

    job_id = str(uuid4())
    job_data = {
        "id": job_id,
        "source": request.source,
        "cron_expression": request.cron_expression,
        "query": request.query,
        "enabled": request.enabled,
    }

    # 캐시에 저장
    await cache.set(
        f"{_SCHEDULE_KEY_PREFIX}{job_id}",
        json.dumps(job_data, ensure_ascii=False),
    )
    # 인덱스에 추가
    await cache.sadd(_SCHEDULE_INDEX_KEY, job_id)

    return {
        "message": "스케줄이 등록되었습니다.",
        **job_data,
    }


@router.put("/jobs/{job_id}")
async def update_schedule_job(
    job_id: str,
    request: ScheduleJobRequest,
    cache: InMemoryCache = Depends(get_cache),
) -> dict:
    """기존 스케줄 작업을 수정한다."""

    # 기존 스케줄 존재 여부 확인
    exists = await cache.exists(f"{_SCHEDULE_KEY_PREFIX}{job_id}")
    if not exists:
        raise HTTPException(status_code=404, detail="스케줄을 찾을 수 없습니다.")

    job_data = {
        "id": job_id,
        "source": request.source,
        "cron_expression": request.cron_expression,
        "query": request.query,
        "enabled": request.enabled,
    }

    # 캐시에 덮어쓰기
    await cache.set(
        f"{_SCHEDULE_KEY_PREFIX}{job_id}",
        json.dumps(job_data, ensure_ascii=False),
    )

    return {
        "message": "스케줄이 수정되었습니다.",
        **job_data,
    }


@router.delete("/jobs/{job_id}")
async def delete_schedule_job(
    job_id: str,
    cache: InMemoryCache = Depends(get_cache),
) -> dict:
    """스케줄 작업을 삭제한다."""

    # 기존 스케줄 존재 여부 확인
    exists = await cache.exists(f"{_SCHEDULE_KEY_PREFIX}{job_id}")
    if not exists:
        raise HTTPException(status_code=404, detail="스케줄을 찾을 수 없습니다.")

    # 캐시에서 삭제
    await cache.delete(f"{_SCHEDULE_KEY_PREFIX}{job_id}")
    await cache.srem(_SCHEDULE_INDEX_KEY, job_id)

    return {"message": "스케줄이 삭제되었습니다.", "id": job_id}
