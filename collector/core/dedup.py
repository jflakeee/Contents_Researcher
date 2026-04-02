"""
중복 제거 모듈

Redis 기반으로 이미 수집한 URL과 본문 해시를 관리하여
동일 컨텐츠의 중복 수집을 방지한다.
"""

import logging
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis 키 접두사
URL_SET_KEY = "cr:dedup:urls"
HASH_SET_KEY = "cr:dedup:hashes"
# 기본 TTL: 30일 (초 단위)
DEFAULT_TTL = 30 * 24 * 60 * 60


class DedupChecker:
    """중복 체크기

    Redis SET을 사용하여 URL과 본문 해시의 중복을 확인한다.
    """

    def __init__(self, redis_client: redis.Redis):
        """초기화

        Args:
            redis_client: Redis 비동기 클라이언트
        """
        self._redis = redis_client

    async def is_url_duplicate(self, url: str) -> bool:
        """URL이 이미 수집된 것인지 확인

        Args:
            url: 확인할 URL

        Returns:
            True면 이미 수집됨 (중복)
        """
        return await self._redis.sismember(URL_SET_KEY, url)

    async def is_hash_duplicate(self, body_hash: str) -> bool:
        """본문 해시가 이미 존재하는지 확인

        Args:
            body_hash: 확인할 SHA-256 해시

        Returns:
            True면 이미 존재 (중복)
        """
        return await self._redis.sismember(HASH_SET_KEY, body_hash)

    async def mark_collected(
        self, url: str, body_hash: Optional[str] = None
    ) -> None:
        """수집 완료 표시

        Args:
            url: 수집한 URL
            body_hash: 본문 해시 (선택)
        """
        await self._redis.sadd(URL_SET_KEY, url)
        if body_hash:
            await self._redis.sadd(HASH_SET_KEY, body_hash)

    async def check_and_mark(
        self, url: str, body_hash: Optional[str] = None
    ) -> bool:
        """중복 확인 후 수집 완료 표시 (원자적 연산)

        Args:
            url: 수집할 URL
            body_hash: 본문 해시 (선택)

        Returns:
            True면 새 컨텐츠 (수집 가능), False면 중복
        """
        # URL 중복 체크
        if await self.is_url_duplicate(url):
            logger.debug("URL 중복: %s", url)
            return False

        # 본문 해시 중복 체크
        if body_hash and await self.is_hash_duplicate(body_hash):
            logger.debug("본문 해시 중복: %s", body_hash[:16])
            return False

        # 중복 아니면 수집 완료 표시
        await self.mark_collected(url, body_hash)
        return True

    async def get_stats(self) -> dict:
        """중복 체크 통계

        Returns:
            {"url_count": int, "hash_count": int}
        """
        url_count = await self._redis.scard(URL_SET_KEY)
        hash_count = await self._redis.scard(HASH_SET_KEY)
        return {"url_count": url_count, "hash_count": hash_count}

    async def clear(self) -> None:
        """모든 중복 데이터 삭제 (테스트용)"""
        await self._redis.delete(URL_SET_KEY, HASH_SET_KEY)
        logger.info("중복 체크 데이터 초기화")
