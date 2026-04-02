"""
감성 분석 메인 모듈

전략 패턴으로 분석 방식을 교체할 수 있다.
- dictionary: KNU 감성사전 기반 (초기 구현)
- model: ML 모델 기반 (Phase 6 고도화)
"""

import logging
from typing import Optional

from shared.types import SentimentResult
from analyzer.sentiment.dictionary import DictionarySentiment

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """감성 분석기

    전략 패턴으로 분석 방식을 선택할 수 있다.
    초기에는 KNU 감성사전 기반으로 동작하며,
    추후 ML 모델로 교체 가능하다.
    """

    def __init__(
        self,
        strategy: str = "dictionary",
        threshold: float = 0.1,
    ):
        """초기화

        Args:
            strategy: 분석 전략 ("dictionary" 또는 "model")
            threshold: 감성 분류 임계값
        """
        self._strategy = strategy
        self._threshold = threshold
        self._analyzer = None

    def _get_analyzer(self):
        """분석기 인스턴스 (지연 초기화)"""
        if self._analyzer is None:
            if self._strategy == "dictionary":
                self._analyzer = DictionarySentiment(threshold=self._threshold)
            elif self._strategy == "model":
                # Phase 6에서 ML 모델 구현
                logger.warning("ML 모델 미구현, dictionary로 폴백")
                self._analyzer = DictionarySentiment(threshold=self._threshold)
            else:
                raise ValueError(f"지원하지 않는 분석 전략: {self._strategy}")

            logger.info("감성 분석기 초기화: strategy=%s", self._strategy)
        return self._analyzer

    def analyze(self, text: str) -> SentimentResult:
        """텍스트 감성 분석

        Args:
            text: 분석할 텍스트

        Returns:
            SentimentResult (label, score, details)
        """
        analyzer = self._get_analyzer()
        label, score, details = analyzer.analyze(text)

        return SentimentResult(
            label=label,
            score=score,
            details=details,
        )

    def analyze_batch(self, texts: list[str]) -> list[SentimentResult]:
        """여러 텍스트 일괄 감성 분석

        Args:
            texts: 분석할 텍스트 목록

        Returns:
            SentimentResult 목록
        """
        return [self.analyze(text) for text in texts]

    @property
    def strategy(self) -> str:
        """현재 분석 전략"""
        return self._strategy

    def set_threshold(self, threshold: float) -> None:
        """감성 분류 임계값 변경

        Args:
            threshold: 새 임계값 (0.0 ~ 1.0)
        """
        self._threshold = threshold
        # 분석기 재초기화
        self._analyzer = None
        logger.info("감성 임계값 변경: %f", threshold)
