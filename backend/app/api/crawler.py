"""
크롤러 API 라우터.
수집 작업 트리거, 상태 확인, 이력 조회 엔드포인트를 제공한다.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.keyword import CollectionJob
from app.schemas.search import CrawlerTriggerRequest

router = APIRouter(prefix="/api/v1/crawler", tags=["crawler"])


@router.post("/trigger")
async def trigger_crawler(
    request: CrawlerTriggerRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """크롤러 수집 작업을 생성(트리거)한다."""

    # 새 수집 작업 레코드 생성
    job = CollectionJob(
        source=request.source,
        status="pending",
        started_at=datetime.now(tz=timezone.utc),
        metadata_={
            "query": request.query,
            "date_from": request.date_from.isoformat() if request.date_from else None,
            "date_to": request.date_to.isoformat() if request.date_to else None,
        },
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    return {
        "job_id": job.id,
        "status": job.status,
        "source": job.source,
        "message": "수집 작업이 생성되었습니다.",
    }


@router.get("/status")
async def get_crawler_status(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """현재 실행 중인(pending/running) 수집 작업 목록을 반환한다."""

    query = (
        select(CollectionJob)
        .where(CollectionJob.status.in_(["pending", "running"]))
        .order_by(CollectionJob.started_at.desc())
    )
    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        {
            "job_id": job.id,
            "source": job.source,
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "items_count": job.items_count,
        }
        for job in jobs
    ]


@router.get("/history")
async def get_crawler_history(
    limit: int = Query(default=20, ge=1, le=100, description="최대 반환 건수"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """최근 수집 작업 이력을 반환한다."""

    query = (
        select(CollectionJob)
        .order_by(CollectionJob.started_at.desc().nulls_last())
        .limit(limit)
    )
    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        {
            "job_id": job.id,
            "source": job.source,
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "items_count": job.items_count,
            "error_message": job.error_message,
        }
        for job in jobs
    ]
