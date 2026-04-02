"""
감성 분석기 테스트

SentimentAnalyzer와 DictionarySentiment의 분석 정확성을 테스트한다.
"""

import pytest

from shared.types import SentimentResult
from analyzer.sentiment.analyzer import SentimentAnalyzer
from analyzer.sentiment.dictionary import DictionarySentiment


class TestDictionarySentiment:
    """KNU 감성사전 기반 분석 테스트"""

    @pytest.fixture
    def analyzer(self):
        return DictionarySentiment(threshold=0.1)

    def test_positive_text(self, analyzer):
        """긍정 텍스트 분류"""
        text = "이 영상 정말 좋아요! 최고의 컨텐츠입니다. 감동적이에요."
        label, score, details = analyzer.analyze(text)

        assert label == "positive"
        assert score > 0.0
        assert details["positive"] > details["negative"]

    def test_negative_text(self, analyzer):
        """부정 텍스트 분류"""
        text = "별로예요. 너무 실망스럽고 지루합니다. 최악이에요."
        label, score, details = analyzer.analyze(text)

        assert label == "negative"
        assert score < 0.0
        assert details["negative"] > details["positive"]

    def test_neutral_text(self, analyzer):
        """중립 텍스트 분류"""
        text = "오늘 날씨가 흐립니다. 내일은 비가 온다고 합니다."
        label, score, details = analyzer.analyze(text)

        assert label == "neutral"

    def test_negation_reversal(self, analyzer):
        """부정어 극성 반전"""
        # "안 좋다"는 부정이어야 함
        text = "안 좋아요"
        label, score, _ = analyzer.analyze(text)
        assert score <= 0.0

    def test_empty_text(self, analyzer):
        """빈 텍스트 → 중립"""
        label, score, details = analyzer.analyze("")
        assert label == "neutral"
        assert score == 0.0

    def test_score_range(self, analyzer):
        """점수 범위 확인 (-1.0 ~ 1.0)"""
        texts = [
            "최고 최고 최고 정말 좋아요 대박 감동",
            "최악 최악 최악 별로 싫어요 실망",
            "오늘 날씨입니다",
        ]
        for text in texts:
            _, score, _ = analyzer.analyze(text)
            assert -1.0 <= score <= 1.0


class TestSentimentAnalyzer:
    """통합 감성 분석기 테스트"""

    def test_default_strategy(self):
        """기본 전략이 dictionary인지 확인"""
        analyzer = SentimentAnalyzer()
        assert analyzer.strategy == "dictionary"

    def test_analyze_returns_sentiment_result(self):
        """분석 결과가 SentimentResult 타입인지 확인"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("좋은 영상이에요!")

        assert isinstance(result, SentimentResult)
        assert result.label in ("positive", "negative", "neutral")
        assert isinstance(result.score, float)
        assert result.details is not None

    def test_analyze_batch(self):
        """배치 분석"""
        analyzer = SentimentAnalyzer()
        texts = ["좋아요!", "별로에요", "그냥 그래요"]
        results = analyzer.analyze_batch(texts)

        assert len(results) == 3
        assert all(isinstance(r, SentimentResult) for r in results)

    def test_set_threshold(self):
        """임계값 변경"""
        analyzer = SentimentAnalyzer(threshold=0.1)
        analyzer.set_threshold(0.3)
        assert analyzer._threshold == 0.3
