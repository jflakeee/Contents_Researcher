"""
컨텐츠 유형 분류기

게시글 제목과 키워드를 분석하여 정보성(informative) 또는 흥미성(entertaining)으로 분류한다.

정보성: 뉴스, 정보, 팁, 가이드, 리뷰, 분석, 비교, 추천, 방법, 설명 등
흥미성: 유머, 짤, 레전드, 대박, ㅋㅋ, 반전, 소름, 충격, 논란, 썰 등
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 컨텐츠 유형 상수
TYPE_INFORMATIVE = "informative"  # 정보성
TYPE_ENTERTAINING = "entertaining"  # 흥미성

# 정보성 키워드 (제목에 포함되면 정보성으로 분류)
INFORMATIVE_KEYWORDS = {
    # 뉴스/보도
    "속보", "뉴스", "보도", "기사", "발표", "공식", "확정", "결정",
    # 정보/지식
    "정보", "팁", "방법", "가이드", "설명", "정리", "요약", "분석",
    "비교", "추천", "리뷰", "후기", "평가", "장단점",
    # 기술/전문
    "업데이트", "패치", "출시", "스펙", "성능", "테스트", "벤치마크",
    # 경제/사회
    "주가", "환율", "금리", "부동산", "정책", "법안", "규제",
    "통계", "데이터", "조사", "연구", "보고서",
    # 교육
    "강의", "튜토리얼", "강좌", "배우기", "입문",
}

# 흥미성 키워드 (제목에 포함되면 흥미성으로 분류)
ENTERTAINING_KEYWORDS = {
    # 유머/재미
    "ㅋㅋ", "ㅎㅎ", "웃긴", "유머", "짤", "짤방", "웃음",
    "레전드", "레전", "ㄹㅈㄷ", "개웃",
    # 감탄/반응
    "대박", "소름", "충격", "반전", "놀라운", "미쳤", "실화",
    "헐", "ㄷㄷ", "ㅇㅈ", "인정",
    # 논란/이슈
    "논란", "썰", "사건", "폭로", "고발", "갑질",
    # 엔터테인먼트
    "직캠", "떡밥", "티저", "예고", "비하인드", "움짤",
    "밈", "드립", "패러디",
    # 일상/공감
    "공감", "현실", "일상", "꿀팁", "핫플",
    # 파일 확장자 (이미지/영상 게시글)
    "jpg", "jpeg", "png", "gif", "mp4", "webm",
}

# 정보성 출처 (이 커뮤니티에서 온 게시글은 정보성 가중치 증가)
INFORMATIVE_SOURCES = {"bobae", "slr", "clien", "inven"}

# 흥미성 출처 (이 커뮤니티에서 온 게시글은 흥미성 가중치 증가)
ENTERTAINING_SOURCES = {"theqoo", "fmkorea", "instiz", "ppomppu", "todayhumor", "ruliweb"}


def classify_content(
    title: str,
    keywords: Optional[list[str]] = None,
    origin_source: Optional[str] = None,
) -> str:
    """컨텐츠를 정보성 또는 흥미성으로 분류

    Args:
        title: 게시글 제목
        keywords: 추출된 키워드 목록
        origin_source: 원본 커뮤니티 (theqoo, fmkorea 등)

    Returns:
        "informative" 또는 "entertaining"
    """
    title_lower = title.lower()
    info_score = 0.0
    enter_score = 0.0

    # 1. 제목 키워드 매칭
    for kw in INFORMATIVE_KEYWORDS:
        if kw in title_lower:
            info_score += 1.0

    for kw in ENTERTAINING_KEYWORDS:
        if kw in title_lower:
            enter_score += 1.0

    # 2. 추출된 키워드 매칭
    if keywords:
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in INFORMATIVE_KEYWORDS:
                info_score += 0.5
            if kw_lower in ENTERTAINING_KEYWORDS:
                enter_score += 0.5

    # 3. 출처 기반 가중치
    if origin_source:
        if origin_source in INFORMATIVE_SOURCES:
            info_score += 0.5
        if origin_source in ENTERTAINING_SOURCES:
            enter_score += 0.5

    # 4. 제목 패턴 기반 추가 판단
    # 물음표가 많으면 정보성 (질문/가이드)
    if title.count("?") >= 1 or "어떻게" in title or "뭐가" in title:
        info_score += 0.3

    # 느낌표가 많으면 흥미성
    if title.count("!") >= 2:
        enter_score += 0.3

    # 이미지/영상 파일명이 포함되면 흥미성
    if re.search(r'\.(jpg|jpeg|png|gif|mp4|webm)\b', title_lower):
        enter_score += 0.5

    # 5. 최종 분류
    if info_score > enter_score:
        return TYPE_INFORMATIVE
    elif enter_score > info_score:
        return TYPE_ENTERTAINING
    else:
        # 동점이면 댓글 수 기준 — 댓글 많으면 흥미성
        return TYPE_ENTERTAINING
