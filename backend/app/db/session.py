"""
데이터베이스 세션 및 In-Memory 캐시 관리 모듈.
SQLAlchemy 2.0 비동기 엔진(SQLite)과 Redis 대체 캐시를 제공한다.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any, Optional

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


class InMemoryCache:
    """Redis 대체 In-Memory 캐시

    Redis의 주요 인터페이스(get/set/sadd/sismember/smembers/delete/srem/scard/exists)를
    딕셔너리 기반으로 구현한다. Docker 없이 로컬 실행 가능하도록 함.
    """

    def __init__(self):
        # 문자열 키-값 저장소
        self._store: dict[str, str] = {}
        # SET 저장소
        self._sets: dict[str, set[str]] = {}

    async def get(self, key: str) -> Optional[str]:
        """문자열 값 조회"""
        return self._store.get(key)

    async def set(self, key: str, value: str, **kwargs) -> None:
        """문자열 값 저장"""
        self._store[key] = value

    async def delete(self, *keys: str) -> None:
        """키 삭제"""
        for key in keys:
            self._store.pop(key, None)
            self._sets.pop(key, None)

    async def exists(self, key: str) -> bool:
        """키 존재 확인"""
        return key in self._store or key in self._sets

    async def sadd(self, key: str, *values: str) -> int:
        """SET에 값 추가"""
        if key not in self._sets:
            self._sets[key] = set()
        before = len(self._sets[key])
        self._sets[key].update(values)
        return len(self._sets[key]) - before

    async def srem(self, key: str, *values: str) -> int:
        """SET에서 값 제거"""
        if key not in self._sets:
            return 0
        before = len(self._sets[key])
        self._sets[key] -= set(values)
        return before - len(self._sets[key])

    async def sismember(self, key: str, value: str) -> bool:
        """SET 멤버 확인"""
        return value in self._sets.get(key, set())

    async def smembers(self, key: str) -> set[str]:
        """SET 모든 멤버 조회"""
        return set(self._sets.get(key, set()))

    async def scard(self, key: str) -> int:
        """SET 크기 조회"""
        return len(self._sets.get(key, set()))

    async def close(self) -> None:
        """정리 (호환용)"""
        pass


# In-Memory 캐시 싱글톤
_cache: InMemoryCache | None = None


def init_engine() -> AsyncEngine:
    """SQLAlchemy 비동기 엔진을 생성하고 모듈 변수에 저장한다."""
    global engine, async_session_factory
    settings = get_settings()

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        # SQLite는 연결 풀을 사용하지 않으므로 풀 설정 생략
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


def init_cache() -> InMemoryCache:
    """In-Memory 캐시를 초기화하고 모듈 변수에 저장한다."""
    global _cache
    _cache = InMemoryCache()
    return _cache


async def close_cache() -> None:
    """캐시를 정리한다."""
    global _cache
    if _cache is not None:
        await _cache.close()
        _cache = None


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


async def get_cache() -> AsyncGenerator[InMemoryCache, None]:
    """FastAPI Depends용 캐시 제너레이터."""
    if _cache is None:
        raise RuntimeError("캐시가 초기화되지 않았습니다.")
    yield _cache
