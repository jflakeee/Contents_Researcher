"""
NLP 분석 파이프라인

수집된 컨텐츠에 대해 키워드 추출, 감성 분석, 중요도 산정을
순차적으로 실행하는 통합 파이프라인.
"""

import logging
from typing import List

from shared.types import ContentItem
from analyzer.keywords.extractor import KeywordExtractor
from analyzer.sentiment.analyzer import SentimentAnalyzer
from analyzer.importance.scorer import ImportanceScorer

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """NLP 분석 파이프라인

    수집기에서 넘겨받은 ContentItem 목록에 대해
    키워드 추출 → 감성 분석 → 중요도 산정을 수행한다.
    """

    def __init__(
        self,
        keyword_extractor: KeywordExtractor | None = None,
        sentiment_analyzer: SentimentAnalyzer | None = None,
        importance_scorer: ImportanceScorer | None = None,
    ):
        """초기화

        Args:
            keyword_extractor: 키워드 추출기 (None이면 기본값 생성)
            sentiment_analyzer: 감성 분석기 (None이면 기본값 생성)
            importance_scorer: 중요도 산정기 (None이면 기본값 생성)
        """
        self._keyword_extractor = keyword_extractor or KeywordExtractor()
        self._sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
        self._importance_scorer = importance_scorer or ImportanceScorer()

    async def analyze(self, items: List[ContentItem]) -> List[ContentItem]:
        """컨텐츠 목록 분석

        각 컨텐츠에 대해:
        1. 제목 + 댓글 텍스트에서 키워드 추출
        2. 댓글 전체에 대한 감성 분석
        3. 개별 댓글 감성 분석
        4. 중요도 점수 산정

        Args:
            items: 수집된 ContentItem 목록

        Returns:
            분석 결과가 채워진 ContentItem 목록
        """
        logger.info("분석 파이프라인 시작: %d건", len(items))

        for idx, item in enumerate(items):
            try:
                self._analyze_single(item)
            except Exception as e:
                logger.warning(
                    "분석 실패 [%d/%d] (source_id=%s): %s",
                    idx + 1,
                    len(items),
                    item.source_id,
                    str(e),
                )

        logger.info("분석 파이프라인 완료: %d건", len(items))
        return items

    def _analyze_single(self, item: ContentItem) -> None:
        """단일 컨텐츠 분석 (in-place 수정)

        Args:
            item: 분석할 ContentItem
        """
        # 댓글 텍스트 결합
        all_comments_text = " ".join(
            comment.body for comment in item.comments if comment.body
        )

        # 분석 대상 텍스트 (제목 + 본문 + 댓글)
        analysis_text = item.title
        if item.body:
            analysis_text += " " + item.body
        if all_comments_text:
            analysis_text += " " + all_comments_text

        # 1단계: 키워드 추출
        item.keywords = self._keyword_extractor.extract(analysis_text)

        # 2단계: 전체 댓글 감성 분석
        if all_comments_text:
            sentiment_result = self._sentiment_analyzer.analyze(all_comments_text)
        else:
            # 댓글이 없으면 제목+본문으로 분석
            sentiment_result = self._sentiment_analyzer.analyze(item.title)

        item.sentiment = sentiment_result.label
        item.sentiment_score = sentiment_result.score

        # 3단계: 개별 댓글 감성 분석
        for comment in item.comments:
            comment_result = self._sentiment_analyzer.analyze(comment.body)
            comment.sentiment = comment_result.label
            comment.sentiment_score = comment_result.score

        # 4단계: 중요도 산정
        item.importance_score = self._importance_scorer.score(item)
