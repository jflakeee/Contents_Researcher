"""
데이터베이스 세션 및 Redis 연결 관리 모듈.
SQLAlchemy 2.0 비동기 엔진과 세션 팩토리를 제공한다.
"""

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

# 비동기 엔진 (앱 시작 시 초기화)
engine: AsyncEngine | None = None

# 비동기 세션 팩토리
async_session_factory: async_sessionmaker[AsyncSession] | None = None

# Redis 클라이언트
redis_client: aioredis.Redis | None = None


def init_engine() -> AsyncEngine:
    """SQLAlchemy 비동기 엔진을 생성하고 모듈 변수에 저장한다."""
    global engine, async_session_factory
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine


async def dispose_engine() -> None:
    """엔진 연결 풀을 정리한다."""
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None


def init_redis() -> aioredis.Redis:
    """Redis 클라이언트를 초기화하고 모듈 변수에 저장한다."""
    global redis_client
    settings = get_settings()
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    return redis_client


async def close_redis() -> None:
    """Redis 연결을 닫는다."""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends용 비동기 DB 세션 제너레이터."""
    if async_session_factory is None:
        raise RuntimeError("데이터베이스 엔진이 초기화되지 않았습니다.")
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI Depends용 Redis 클라이언트 제너레이터."""
    if redis_client is None:
        raise RuntimeError("Redis 클라이언트가 초기화되지 않았습니다.")
    yield redis_client
