"""
키워드 추출기 테스트

KeywordExtractor의 전처리, 명사 추출, 키워드 선별 로직을 테스트한다.
"""

import pytest

from analyzer.keywords.extractor import KeywordExtractor


class TestKeywordExtractor:
    """키워드 추출기 테스트"""

    @pytest.fixture
    def extractor(self):
        """KeyBERT 비활성화한 추출기 (빈도 기반, 테스트 속도 향상)"""
        return KeywordExtractor(top_n=5, use_keybert=False)

    def test_extract_basic(self, extractor):
        """기본 한국어 텍스트에서 키워드 추출"""
        text = "인공지능 기술이 발전하면서 다양한 분야에서 활용되고 있습니다. 인공지능 분야의 발전이 기대됩니다."
        result = extractor.extract(text)

        assert isinstance(result, list)
        assert len(result) > 0
        # 인공지능, 기술, 발전, 분야 등이 추출되어야 함
        assert any("인공" in kw or "기술" in kw or "발전" in kw for kw in result)

    def test_extract_empty_text(self, extractor):
        """빈 텍스트 입력 시 빈 배열 반환"""
        assert extractor.extract("") == []
        assert extractor.extract("   ") == []

    def test_extract_html_removal(self, extractor):
        """HTML 태그 포함 텍스트 처리"""
        text = "<p>인공지능 <b>기술</b>이 <a href='link'>발전</a>합니다.</p>"
        result = extractor.extract(text)

        assert isinstance(result, list)
        # HTML 태그가 키워드로 추출되면 안 됨
        assert all("<" not in kw for kw in result)

    def test_extract_url_removal(self, extractor):
        """URL 포함 텍스트 처리"""
        text = "자세한 내용은 https://example.com/page 에서 확인하세요. 인공지능 기술 관련 내용입니다."
        result = extractor.extract(text)

        assert all("http" not in kw for kw in result)

    def test_extract_respects_top_n(self, extractor):
        """top_n 설정값 이하로 키워드 반환"""
        text = "프로그래밍 언어 파이썬 자바 자바스크립트 루비 고랭 러스트 코틀린 스위프트 타입스크립트"
        result = extractor.extract(text)

        assert len(result) <= 5

    def test_stopwords_filtered(self, extractor):
        """불용어 필터링 확인"""
        text = "것은 수가 등의 때에 것이 인공지능 기술"
        result = extractor.extract(text)

        # 불용어(것, 수, 등, 때)는 제외되어야 함
        assert all(kw not in {"것", "수", "등", "때"} for kw in result)

    def test_preprocess(self, extractor):
        """전처리 메서드 동작 확인"""
        text = "  <br>Hello!!  http://test.com  특수@문자#제거   "
        cleaned = extractor._preprocess(text)

        assert "<br>" not in cleaned
        assert "http" not in cleaned
        assert "@" not in cleaned
        assert "#" not in cleaned
