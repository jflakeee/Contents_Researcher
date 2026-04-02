"""
수집기 추상 베이스 클래스

모든 플랫폼별 수집기는 이 클래스를 상속하여 구현한다.
collect()와 collect_comments()를 반드시 구현해야 한다.
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from shared.types import CollectionResult, ContentItem

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """수집기 추상 베이스 클래스

    새 플랫폼 수집기를 추가하려면:
    1. 이 클래스를 상속
    2. source_name 속성 정의
    3. collect()와 collect_comments() 구현
    4. CollectorRegistry에 등록
    """

    # 수집 출처명 (하위 클래스에서 정의)
    source_name: str = ""

    @abstractmethod
    async def collect(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ContentItem]:
        """컨텐츠 수집

        Args:
            query: 검색 키워드
            date_from: 수집 시작일
            date_to: 수집 종료일

        Returns:
            수집된 컨텐츠 목록
        """
        ...

    @abstractmethod
    async def collect_comments(self, content_id: str) -> List:
        """특정 컨텐츠의 댓글 수집

        Args:
            content_id: 플랫폼 내 컨텐츠 고유 ID

        Returns:
            댓글 목록
        """
        ...

    def compute_body_hash(self, text: str) -> str:
        """본문 텍스트의 SHA-256 해시 생성 (중복 체크용)

        Args:
            text: 해시할 텍스트

        Returns:
            SHA-256 해시 문자열
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def run(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> CollectionResult:
        """수집 → 댓글 수집 → 해시 생성 전체 파이프라인

        분석(NLP)과 DB 저장은 이 메서드를 호출하는 쪽에서 처리한다.

        Args:
            query: 검색 키워드
            date_from: 수집 시작일
            date_to: 수집 종료일

        Returns:
            수집 결과 (성공/실패, 수집 건수)
        """
        result = CollectionResult(source=self.source_name)

        try:
            logger.info(
                "[%s] 수집 시작: query='%s', from=%s, to=%s",
                self.source_name,
                query,
                date_from,
                date_to,
            )

            # 1단계: 컨텐츠 수집
            items = await self.collect(query, date_from, date_to)
            result.collected_count = len(items)
            logger.info("[%s] %d건 수집 완료", self.source_name, len(items))

            # 2단계: 각 컨텐츠별 댓글 수집 + 해시 생성
            for item in items:
                try:
                    # 댓글 수집
                    comments = await self.collect_comments(item.source_id)
                    item.comments = comments
                    item.comment_count = len(comments)

                    # 본문 해시 생성 (중복 체크용)
                    hash_source = item.title
                    if item.body:
                        hash_source += item.body
                    item.body_hash = self.compute_body_hash(hash_source)

                except Exception as e:
                    logger.warning(
                        "[%s] 댓글 수집 실패 (content_id=%s): %s",
                        self.source_name,
                        item.source_id,
                        str(e),
                    )

            result.saved_count = len(items)
            result.success = True
            logger.info("[%s] 수집 파이프라인 완료: %d건", self.source_name, len(items))

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error("[%s] 수집 실패: %s", self.source_name, str(e))

        return result
