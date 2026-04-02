"""
KNU 한국어 감성사전 기반 감성 분석

충남대학교 KNU 한국어 감성사전을 활용하여
텍스트의 감성을 분석한다. (규칙 기반)
"""

import logging
import os
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 내장 감성 사전 (KNU 감성사전 핵심어 기반 축약)
# 실제 운영 시에는 외부 사전 파일 로드로 교체
POSITIVE_WORDS: Dict[str, float] = {
    "좋다": 2.0, "좋은": 2.0, "좋아": 2.0, "최고": 2.0, "훌륭": 2.0,
    "대박": 2.0, "감동": 2.0, "멋지다": 2.0, "멋진": 2.0, "아름답다": 1.5,
    "유익": 1.5, "재미": 1.5, "재밌": 1.5, "웃기": 1.5, "행복": 1.5,
    "사랑": 1.5, "추천": 1.5, "응원": 1.5, "감사": 1.5, "기대": 1.0,
    "편하다": 1.0, "편리": 1.0, "깔끔": 1.0, "완벽": 2.0, "성공": 1.5,
    "흥미": 1.0, "만족": 1.5, "뛰어나다": 2.0, "놀랍다": 1.5, "훈훈": 1.5,
    "인정": 1.0, "공감": 1.0, "소름": 1.0, "ㅋㅋ": 0.5, "ㅎㅎ": 0.5,
    "대단": 1.5, "잘했": 1.5, "예쁘다": 1.5, "이쁘다": 1.5, "신기": 1.0,
}

NEGATIVE_WORDS: Dict[str, float] = {
    "나쁘다": -2.0, "나쁜": -2.0, "별로": -1.5, "싫다": -1.5, "싫어": -1.5,
    "최악": -2.0, "실망": -2.0, "짜증": -1.5, "화나다": -1.5, "화남": -1.5,
    "슬프다": -1.5, "아프다": -1.0, "불편": -1.5, "불만": -1.5, "비추": -2.0,
    "후회": -1.5, "걱정": -1.0, "무섭다": -1.0, "지루": -1.5, "졸리다": -1.0,
    "답답": -1.5, "짜증나다": -2.0, "열받다": -2.0, "쓰레기": -2.0, "혐오": -2.0,
    "거짓": -2.0, "사기": -2.0, "거짓말": -2.0, "쓸모없다": -1.5, "잘못": -1.0,
    "어렵다": -0.5, "힘들다": -1.0, "ㅠㅠ": -0.5, "ㅜㅜ": -0.5,
    "못하다": -1.0, "부족": -1.0, "아쉽다": -1.0, "아쉬운": -1.0,
}

# 부정어 (극성 반전)
NEGATION_WORDS = {"안", "못", "없", "아니", "않", "말", "아닌"}


class DictionarySentiment:
    """KNU 감성사전 기반 감성 분석기

    형태소 분석 후 사전 매칭으로 감성을 판단한다.
    부정어가 감성어 앞에 오면 극성을 반전한다.
    """

    def __init__(
        self,
        positive_dict: Optional[Dict[str, float]] = None,
        negative_dict: Optional[Dict[str, float]] = None,
        threshold: float = 0.1,
    ):
        """초기화

        Args:
            positive_dict: 긍정어 사전 (None이면 내장 사전 사용)
            negative_dict: 부정어 사전 (None이면 내장 사전 사용)
            threshold: 감성 분류 임계값 (기본 ±0.1)
        """
        self._positive = positive_dict or POSITIVE_WORDS
        self._negative = negative_dict or NEGATIVE_WORDS
        self._threshold = threshold
        self._kiwi = None

    def _get_kiwi(self):
        """Kiwipiepy 형태소 분석기 (지연 초기화)"""
        if self._kiwi is None:
            from kiwipiepy import Kiwi
            self._kiwi = Kiwi()
        return self._kiwi

    def analyze(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """텍스트 감성 분석

        Args:
            text: 분석할 텍스트

        Returns:
            (감성 라벨, 감성 점수, 상세 비율)
            - 라벨: "positive", "negative", "neutral"
            - 점수: -1.0 ~ 1.0
            - 비율: {"positive": float, "negative": float, "neutral": float}
        """
        if not text or not text.strip():
            return "neutral", 0.0, {"positive": 0.0, "negative": 0.0, "neutral": 1.0}

        # 형태소 분석
        kiwi = self._get_kiwi()
        result = kiwi.analyze(text)

        if not result or not result[0][0]:
            return "neutral", 0.0, {"positive": 0.0, "negative": 0.0, "neutral": 1.0}

        tokens = result[0][0]
        positive_score = 0.0
        negative_score = 0.0
        total_sentiment_words = 0
        prev_is_negation = False

        for token in tokens:
            form = token.form

            # 부정어 체크
            if form in NEGATION_WORDS:
                prev_is_negation = True
                continue

            # 긍정어 매칭
            score = self._match_sentiment(form)
            if score != 0.0:
                # 부정어가 앞에 있으면 극성 반전
                if prev_is_negation:
                    score = -score

                if score > 0:
                    positive_score += score
                else:
                    negative_score += abs(score)

                total_sentiment_words += 1

            prev_is_negation = False

        # 최종 점수 계산
        if total_sentiment_words == 0:
            return "neutral", 0.0, {"positive": 0.0, "negative": 0.0, "neutral": 1.0}

        # 정규화된 점수 (-1.0 ~ 1.0)
        total = positive_score + negative_score
        if total > 0:
            normalized_score = (positive_score - negative_score) / total
        else:
            normalized_score = 0.0

        # 비율 계산
        total_with_neutral = total_sentiment_words  # 감성어 기준
        pos_ratio = positive_score / total if total > 0 else 0.0
        neg_ratio = negative_score / total if total > 0 else 0.0
        neu_ratio = max(0.0, 1.0 - pos_ratio - neg_ratio)

        details = {
            "positive": round(pos_ratio, 3),
            "negative": round(neg_ratio, 3),
            "neutral": round(neu_ratio, 3),
        }

        # 임계값 기반 라벨 분류
        if normalized_score > self._threshold:
            label = "positive"
        elif normalized_score < -self._threshold:
            label = "negative"
        else:
            label = "neutral"

        return label, round(normalized_score, 4), details

    def _match_sentiment(self, form: str) -> float:
        """단어의 감성 점수 매칭

        Args:
            form: 형태소

        Returns:
            감성 점수 (양수=긍정, 음수=부정, 0=무감성)
        """
        # 긍정어 확인
        if form in self._positive:
            return self._positive[form]

        # 부정어 확인
        if form in self._negative:
            return self._negative[form]

        # 부분 매칭 (어간 기반)
        for word, score in self._positive.items():
            if form.startswith(word) or word.startswith(form):
                if len(form) >= 2:
                    return score

        for word, score in self._negative.items():
            if form.startswith(word) or word.startswith(form):
                if len(form) >= 2:
                    return score

        return 0.0
