"""
FastAPI 애플리케이션 엔트리포인트.
라이프사이클 관리, 미들웨어 설정, 라우터 등록, 예외 핸들러를 정의한다.
"""

import logging
import os
import sys

# 프로젝트 루트를 PYTHONPATH에 추가 (shared, collector, analyzer 모듈 접근용)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.session import (
    close_cache,
    dispose_engine,
    init_cache,
    init_engine,
)

# 라우터 import
from app.api.contents import router as contents_router
from app.api.keywords import router as keywords_router, sources_router
from app.api.crawler import router as crawler_router
from app.api.scheduler import router as scheduler_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """애플리케이션 시작/종료 시 리소스를 초기화/정리한다."""

    # 시작: DB 엔진 및 캐시 초기화
    logger.info("데이터베이스 엔진을 초기화합니다.")
    init_engine()

    # SQLite 사용 시 테이블 자동 생성
    from app.db.session import engine as db_engine
    from app.models.base import Base
    if db_engine and "sqlite" in str(db_engine.url):
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite 테이블을 생성했습니다.")

    logger.info("In-Memory 캐시를 초기화합니다.")
    init_cache()

    # 자동 수집 스케줄러 시작
    from app.services.auto_scheduler import start_auto_scheduler, stop_auto_scheduler
    start_auto_scheduler()

    yield

    # 종료: 자동 수집 스케줄러 정지
    stop_auto_scheduler()

    # 종료: 리소스 정리
    logger.info("캐시를 정리합니다.")
    await close_cache()

    logger.info("데이터베이스 엔진을 종료합니다.")
    await dispose_engine()


def create_app() -> FastAPI:
    """FastAPI 앱 인스턴스를 생성하고 설정한다."""

    settings = get_settings()

    app = FastAPI(
        title="Contents Researcher API",
        description="콘텐츠 수집·분석·검색 API 서버",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS 미들웨어 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(contents_router)
    app.include_router(keywords_router)
    app.include_router(sources_router)
    app.include_router(crawler_router)
    app.include_router(scheduler_router)

    # 루트 헬스체크 엔드포인트
    @app.get("/")
    async def root() -> dict:
        """서비스 상태 확인용 루트 엔드포인트."""
        return {"status": "ok", "service": "Contents Researcher API"}

    # 전역 예외 핸들러: 예상치 못한 에러를 500으로 반환
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """처리되지 않은 예외를 잡아 500 응답을 반환한다."""
        logger.exception("처리되지 않은 예외 발생: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "내부 서버 오류가 발생했습니다."},
        )

    return app


# uvicorn에서 직접 참조할 앱 인스턴스
app = create_app()
