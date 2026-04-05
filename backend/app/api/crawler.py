"""
크롤러 API 라우터.
수집 작업 트리거, 상태 확인, 이력 조회 엔드포인트를 제공한다.
"""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.keyword import CollectionJob
from app.schemas.search import CrawlerTriggerRequest

router = APIRouter(prefix="/api/v1/crawler", tags=["crawler"])


@router.post("/trigger")
async def trigger_crawler(
    request: CrawlerTriggerRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """크롤러 수집 작업을 백그라운드에서 시작한다.
    job은 collection_service 내부에서 생성/관리된다."""

    # 백그라운드에서 실제 수집 실행 (job 생성 포함)
    background_tasks.add_task(
        _run_collection_task,
        source=request.source,
        query=request.query or "",
    )

    return {
        "source": request.source,
        "status": "running",
        "message": "수집 작업이 시작되었습니다.",
    }


async def _run_collection_task(source: str, query: str) -> None:
    """백그라운드에서 수집 파이프라인을 실행하는 태스크"""
    from app.services.collection_service import run_collection
    await run_collection(source=source, query=query)


@router.post("/bulk")
async def trigger_bulk_collection(
    background_tasks: BackgroundTasks,
) -> dict:
    """한달 전 ~ 1주 전 게시글 대량 수집을 백그라운드에서 시작한다."""
    background_tasks.add_task(_run_bulk_task)
    return {"message": "대량 수집이 시작되었습니다. 수집 이력에서 진행 상황을 확인하세요."}


async def _run_bulk_task() -> None:
    """백그라운드 대량 수집 태스크"""
    from app.services.bulk_collection import bulk_collect_and_save
    await bulk_collect_and_save()


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
            "id": job.id,
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
            "id": job.id,
            "source": job.source,
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "items_count": job.items_count,
            "error_message": job.error_message,
        }
        for job in jobs
    ]
