"""
키워드 추출기

Kiwipiepy 형태소 분석과 KeyBERT 임베딩을 활용하여
텍스트에서 핵심 키워드를 추출한다.
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# 한국어 불용어 목록
STOPWORDS_KO = {
    "것", "수", "등", "때", "거", "좀", "씨", "말", "그", "이", "저",
    "더", "또", "다", "에서", "로", "을", "를", "이", "가", "은", "는",
    "도", "에", "의", "와", "과", "한", "하다", "되다", "있다", "없다",
    "ㅋ", "ㅎ", "ㅠ", "ㅡ", "ㄱ", "ㄴ",
    "아", "음", "네", "예", "뭐", "나", "진짜", "너무", "완전", "정말",
}


class KeywordExtractor:
    """키워드 추출기

    텍스트를 형태소 분석하여 명사를 추출하고,
    KeyBERT로 문맥 기반 핵심 키워드를 선별한다.
    """

    def __init__(
        self,
        top_n: int = 15,
        use_keybert: bool = True,
        stopwords: Optional[set] = None,
    ):
        """초기화

        Args:
            top_n: 추출할 키워드 수
            use_keybert: KeyBERT 사용 여부 (False면 빈도 기반만 사용)
            stopwords: 불용어 집합 (None이면 기본 불용어 사용)
        """
        self._top_n = top_n
        self._use_keybert = use_keybert
        self._stopwords = stopwords or STOPWORDS_KO
        self._kiwi = None
        self._keybert_model = None

    def _get_kiwi(self):
        """Kiwipiepy 형태소 분석기 (지연 초기화)"""
        if self._kiwi is None:
            from kiwipiepy import Kiwi
            self._kiwi = Kiwi()
            logger.info("Kiwipiepy 형태소 분석기 초기화 완료")
        return self._kiwi

    def _get_keybert(self):
        """KeyBERT 모델 (지연 초기화)"""
        if self._keybert_model is None and self._use_keybert:
            from keybert import KeyBERT
            self._keybert_model = KeyBERT("paraphrase-multilingual-MiniLM-L12-v2")
            logger.info("KeyBERT 모델 초기화 완료")
        return self._keybert_model

    def extract(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출

        Args:
            text: 분석할 텍스트

        Returns:
            추출된 키워드 목록 (중요도 순)
        """
        if not text or not text.strip():
            return []

        # 1단계: 텍스트 전처리
        cleaned = self._preprocess(text)
        if not cleaned:
            return []

        # 2단계: KeyBERT 사용 가능하면 임베딩 기반 추출
        if self._use_keybert:
            try:
                return self._extract_with_keybert(cleaned)
            except Exception as e:
                logger.warning("KeyBERT 추출 실패, 빈도 기반으로 폴백: %s", str(e))

        # 3단계: 빈도 기반 추출 (폴백)
        return self._extract_by_frequency(cleaned)

    def _preprocess(self, text: str) -> str:
        """텍스트 전처리

        Args:
            text: 원본 텍스트

        Returns:
            정제된 텍스트
        """
        # HTML 태그 제거
        text = re.sub(r"<[^>]+>", " ", text)
        # URL 제거
        text = re.sub(r"https?://\S+", " ", text)
        # 특수문자 정리 (한글, 영문, 숫자, 공백만 유지)
        text = re.sub(r"[^\w\s가-힣a-zA-Z0-9]", " ", text)
        # 연속 공백 정리
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_nouns(self, text: str) -> List[str]:
        """형태소 분석으로 명사 추출

        Args:
            text: 전처리된 텍스트

        Returns:
            추출된 명사 목록 (중복 포함)
        """
        kiwi = self._get_kiwi()
        result = kiwi.analyze(text)

        nouns = []
        if result:
            # 분석 결과에서 명사(NNG, NNP)와 외래어(SL) 추출
            for token in result[0][0]:
                # token: (형태소, 품사태그, 시작위치, 길이)
                form = token.form
                tag = token.tag

                # 명사, 고유명사, 외래어 추출
                if tag in ("NNG", "NNP", "SL") and len(form) >= 2:
                    # 불용어 필터링
                    if form.lower() not in self._stopwords:
                        nouns.append(form)

        return nouns

    def _extract_with_keybert(self, text: str) -> List[str]:
        """KeyBERT로 핵심 키워드 추출

        Args:
            text: 전처리된 텍스트

        Returns:
            키워드 목록 (유사도 순)
        """
        # 형태소 분석으로 후보 키워드 추출
        nouns = self._extract_nouns(text)
        if not nouns:
            return []

        # 중복 제거된 후보 목록
        candidates = list(set(nouns))

        # KeyBERT로 문서와 가장 관련 높은 키워드 선별
        keybert = self._get_keybert()
        keywords = keybert.extract_keywords(
            text,
            candidates=candidates,
            top_n=self._top_n,
            use_mmr=True,           # 다양성 확보 (Maximal Marginal Relevance)
            diversity=0.5,
        )

        # (keyword, score) 튜플에서 키워드만 추출
        return [kw[0] for kw in keywords]

    def _extract_by_frequency(self, text: str) -> List[str]:
        """빈도 기반 키워드 추출 (KeyBERT 폴백)

        Args:
            text: 전처리된 텍스트

        Returns:
            키워드 목록 (빈도 순)
        """
        from collections import Counter

        nouns = self._extract_nouns(text)
        if not nouns:
            return []

        # 빈도 기반 상위 N개
        counter = Counter(nouns)
        return [word for word, _ in counter.most_common(self._top_n)]
