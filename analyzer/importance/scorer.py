"""
중요도 산정 모듈

컨텐츠의 여러 지표를 가중 합산하여 중요도 점수를 산출한다.
가중치는 /settings 페이지에서 관리자가 조정 가능하다.
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from shared.constants import DEFAULT_IMPORTANCE_WEIGHTS
from shared.types import ContentItem

logger = logging.getLogger(__name__)


class ImportanceScorer:
    """중요도 산정기

    중요도 = w1*정규화(댓글수) + w2*정규화(좋아요수) + w3*감성편향도
           + w4*키워드관련성 + w5*최신성

    각 지표는 0.0 ~ 1.0으로 정규화한 뒤 가중 합산하여
    최종 0.0 ~ 10.0 범위의 점수를 산출한다.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        max_comment_count: int = 1000,
        max_like_count: int = 10000,
        recency_half_life_days: int = 7,
    ):
        """초기화

        Args:
            weights: 가중치 딕셔너리 (None이면 기본값 사용)
            max_comment_count: 정규화 기준 최대 댓글 수
            max_like_count: 정규화 기준 최대 좋아요 수
            recency_half_life_days: 최신성 반감기 (일)
        """
        self._weights = weights or DEFAULT_IMPORTANCE_WEIGHTS.copy()
        self._max_comment = max_comment_count
        self._max_like = max_like_count
        self._half_life = recency_half_life_days

    def score(self, item: ContentItem) -> float:
        """컨텐츠 중요도 점수 산출

        Args:
            item: 분석된 ContentItem (키워드, 감성 점수 포함)

        Returns:
            중요도 점수 (0.0 ~ 10.0)
        """
        w = self._weights

        # 1. 댓글 수 정규화 (로그 스케일)
        comment_norm = self._log_normalize(item.comment_count, self._max_comment)

        # 2. 좋아요 수 정규화 (로그 스케일)
        like_norm = self._log_normalize(item.like_count, self._max_like)

        # 3. 감성 편향도 (절대값이 클수록 분명한 반응 = 높은 관심)
        sentiment_bias = abs(item.sentiment_score) if item.sentiment_score else 0.0

        # 4. 키워드 관련성 (추출된 키워드 수 / 목표 키워드 수)
        keyword_relevance = min(len(item.keywords) / 15.0, 1.0) if item.keywords else 0.0

        # 5. 최신성 (지수 감쇠)
        recency = self._compute_recency(item.collected_at)

        # 가중 합산 (0.0 ~ 1.0 범위)
        raw_score = (
            w.get("comment_count", 0.25) * comment_norm
            + w.get("like_count", 0.20) * like_norm
            + w.get("sentiment_bias", 0.15) * sentiment_bias
            + w.get("keyword_relevance", 0.25) * keyword_relevance
            + w.get("recency", 0.15) * recency
        )

        # 0.0 ~ 10.0 범위로 스케일링
        final_score = round(raw_score * 10.0, 2)
        return min(max(final_score, 0.0), 10.0)

    def _log_normalize(self, value: int, max_value: int) -> float:
        """로그 스케일 정규화

        소수의 컨텐츠가 매우 높은 수치를 가지는 경우를 완화한다.

        Args:
            value: 정규화할 값
            max_value: 기준 최대값

        Returns:
            0.0 ~ 1.0 범위의 정규화 값
        """
        if value <= 0:
            return 0.0
        if max_value <= 0:
            return 0.0
        normalized = math.log1p(value) / math.log1p(max_value)
        return min(normalized, 1.0)

    def _compute_recency(self, collected_at: datetime) -> float:
        """최신성 점수 계산 (지수 감쇠)

        반감기를 기준으로 오래된 컨텐츠일수록 낮은 점수를 부여한다.

        Args:
            collected_at: 수집 시각

        Returns:
            0.0 ~ 1.0 범위의 최신성 점수
        """
        now = datetime.now(tz=timezone.utc)
        age_days = (now - collected_at).total_seconds() / 86400.0

        if age_days <= 0:
            return 1.0

        # 지수 감쇠: score = 0.5 ^ (age / half_life)
        decay = math.pow(0.5, age_days / self._half_life)
        return decay

    def update_weights(self, weights: Dict[str, float]) -> None:
        """가중치 업데이트 (/settings에서 호출)

        Args:
            weights: 새 가중치 딕셔너리
        """
        self._weights.update(weights)
        logger.info("중요도 가중치 업데이트: %s", self._weights)
