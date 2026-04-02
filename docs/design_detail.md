# Contents Researcher - 상세 구현 명세

## 1. 백엔드 (FastAPI) 상세

### 1.1 엔트리포인트 (main.py)
```python
# FastAPI 앱 초기화
# - CORS 미들웨어 (프론트엔드 localhost:3000 허용)
# - 라우터 등록 (/api/v1/contents, /api/v1/keywords, /api/v1/crawler, /api/v1/scheduler)
# - lifespan 이벤트: DB 연결 풀 초기화, Redis 연결, APScheduler 시작
# - 예외 핸들러 등록
```

### 1.2 환경설정 (config.py)
```python
# pydantic-settings 기반 Settings 클래스
# - DATABASE_URL: PostgreSQL 연결 문자열
# - REDIS_URL: Redis 연결 문자열
# - YOUTUBE_API_KEY: YouTube Data API v3 키
# - INSTAGRAM_ACCESS_TOKEN: 인스타그램 API 토큰
# - CORS_ORIGINS: 허용 origin 목록
# - SCHEDULER_TIMEZONE: 스케줄러 시간대 (Asia/Seoul)
# .env 파일에서 로드
```

### 1.3 DB 세션 (db/session.py)
```python
# SQLAlchemy 2.0 비동기 엔진
# - create_async_engine(DATABASE_URL)
# - async_sessionmaker로 세션 팩토리
# - get_db() 의존성 주입용 제너레이터
```

### 1.4 API 라우터 상세

#### contents.py
```python
# POST /api/v1/contents/search
# - 요청: SearchRequest (query, sources[], sentiment, date_from, date_to, sort_by, page, page_size)
# - 응답: PaginatedResponse[ContentSummary]
# - 로직: GIN 인덱스 키워드 검색 + 필터 조합, TimescaleDB time_bucket 활용

# GET /api/v1/contents/{id}
# - 응답: ContentDetail (기본 정보 + 댓글 목록 + 키워드 하이라이트)
# - Redis 캐싱 (TTL 5분)

# GET /api/v1/contents/trending
# - 쿼리파라미터: period (day/week/month), source, limit
# - 로직: importance_score 기준 상위 N개
```

#### keywords.py
```python
# GET /api/v1/keywords/top
# - 쿼리파라미터: period, source, limit
# - 로직: keyword_trends 테이블에서 count 기준 상위

# GET /api/v1/keywords/trend
# - 쿼리파라미터: keyword, period
# - 응답: 일별 키워드 빈도 시계열 데이터 (차트용)
```

#### crawler.py
```python
# POST /api/v1/crawler/trigger
# - 요청: {source: "youtube", query: "검색어", date_range: {...}}
# - 로직: 백그라운드 태스크로 수집기 실행, job ID 반환

# GET /api/v1/crawler/status
# - 응답: 현재 실행 중인 수집 작업 목록

# GET /api/v1/crawler/history
# - 응답: collection_jobs 테이블에서 최근 이력
```

#### scheduler.py
```python
# CRUD: 스케줄 관리
# - APScheduler의 job store에서 조회/추가/수정/삭제
# - cron 표현식 검증
```

---

## 2. 크롤러/수집기 상세

### 2.1 BaseCollector (core/base.py)
```python
from abc import ABC, abstractmethod
from typing import List
from shared.types import ContentItem, Comment

class BaseCollector(ABC):
    """모든 수집기의 추상 베이스 클래스"""
    
    source_name: str  # "youtube", "aggag" 등
    
    @abstractmethod
    async def collect(self, query: str, date_from: datetime, date_to: datetime) -> List[ContentItem]:
        """컨텐츠 수집"""
        ...
    
    @abstractmethod
    async def collect_comments(self, content_id: str) -> List[Comment]:
        """댓글 수집"""
        ...
    
    async def save(self, items: List[ContentItem]) -> int:
        """DB 저장 (공통 로직). 중복 체크 후 저장. 저장된 건수 반환"""
        ...
    
    async def run(self, query: str, date_from: datetime, date_to: datetime) -> int:
        """수집 → 분석 → 저장 전체 파이프라인"""
        items = await self.collect(query, date_from, date_to)
        for item in items:
            item.comments = await self.collect_comments(item.source_id)
        # NLP 분석 파이프라인 호출
        analyzed = await analyze_pipeline(items)
        return await self.save(analyzed)
```

### 2.2 수집기 플러그인 등록 (core/registry.py)
```python
# CollectorRegistry: 수집기 등록/조회
# - register(name, collector_class)
# - get(name) -> BaseCollector
# - list_all() -> Dict[str, BaseCollector]
# 새 수집기 추가 시 registry에 등록만 하면 API에서 자동 사용 가능
```

### 2.3 중복 제거 (core/dedup.py)
```python
# Redis 기반 중복 체크
# - URL 해시로 1차 체크 (SET)
# - body_hash로 2차 체크 (유사 컨텐츠 감지)
# - TTL 설정으로 오래된 해시 자동 정리
```

### 2.4 YouTubeCollector (youtube/collector.py)
```python
# YouTube Data API v3 사용
# - search().list(): 키워드 검색, 날짜 필터
# - videos().list(): 영상 상세 (조회수, 좋아요 등)
# - commentThreads().list(): 댓글 수집
# - 일일 할당량 10,000 유닛 관리 (사용량 추적)
# 
# 파싱: youtube/parser.py
# - API 응답 → ContentItem 변환
# - 썸네일 URL, 채널 정보 등 metadata에 저장
```

### 2.5 AggagCollector (aggag/collector.py)
```python
# Playwright 기반 동적 페이지 스크래핑
# - 페이지 로드 → 게시글 목록 추출
# - 각 게시글 상세 페이지 → 제목, 본문, 댓글 추출
# - 페이지네이션 처리
# - rate limiting (요청 간 딜레이)
#
# 파싱: aggag/parser.py
# - HTML → ContentItem 변환
# - BeautifulSoup으로 구조화된 데이터 추출
```

### 2.6 InstagramCollector (instagram/collector.py)
```python
# Instagram Basic Display API + Playwright 폴백
# - API: 공개 피드, 해시태그 검색
# - Playwright: API 제한 시 공개 프로필 스크래핑
# - 이미지/영상 메타데이터, 캡션, 댓글 수집
```

### 2.7 스케줄링 (core/scheduler.py)
```python
# APScheduler 설정
# - SQLAlchemyJobStore: PostgreSQL에 job 영속화
# - AsyncIOScheduler: 비동기 실행
# 
# 기본 스케줄:
# - 유튜브: 6시간마다 (cron hour='*/6')
# - aggag.com: 3시간마다 (cron hour='*/3')
# - 인스타그램: 12시간마다 (cron hour='0,12')
# - 키워드 트렌드 집계: 매일 자정 (cron hour=0, minute=0)
```

---

## 3. NLP 분석기 상세

### 3.1 키워드 추출 (keywords/extractor.py)
```python
# 파이프라인:
# 1. 텍스트 전처리: HTML 태그 제거, 특수문자 정리
# 2. Kiwipiepy 형태소 분석: 명사(NNG, NNP), 복합어 추출
# 3. 불용어 제거: 한국어 불용어 사전
# 4. KeyBERT 임베딩: sentence-transformers로 문서-키워드 유사도 계산
# 5. 상위 N개 키워드 반환 (기본 10개)
#
# 댓글 키워드: 개별 댓글이 아닌 전체 댓글을 합쳐서 추출
```

### 3.2 감성 분석 (sentiment/analyzer.py)
```python
# SentimentAnalyzer: 전략 패턴으로 분석 방식 교체 가능

class SentimentAnalyzer:
    def __init__(self, strategy: str = "dictionary"):
        # "dictionary": KNU 감성사전 기반
        # "model": ML 모델 기반 (Phase 6)
    
    def analyze(self, text: str) -> SentimentResult:
        # 반환: (sentiment: str, score: float)
        # sentiment: "positive" | "negative" | "neutral"
        # score: -1.0 (매우 부정) ~ 1.0 (매우 긍정)
```

### 3.3 KNU 감성사전 기반 (sentiment/dictionary.py)
```python
# KNU 한국어 감성사전 로드
# - 긍정어 사전, 부정어 사전
# - Kiwipiepy로 형태소 분석 후 사전 매칭
# - 부정어(안, 못, 없 등) 앞 감성어 극성 반전
# - 최종 점수 = (긍정 점수 합 - 부정 점수 합) / 전체 감성어 수
```

### 3.4 중요도 산정 (importance/scorer.py)
```python
# 중요도 = w1*정규화(댓글수) + w2*정규화(좋아요수) + w3*감성편향도 + w4*키워드관련성 + w5*최신성
#
# 기본 가중치:
# w1 = 0.25 (댓글수)
# w2 = 0.20 (좋아요수)
# w3 = 0.15 (감성편향도: abs(sentiment_score))
# w4 = 0.25 (키워드관련성: KeyBERT 유사도)
# w5 = 0.15 (최신성: 수집일 기준 감쇠)
#
# 가중치는 settings 페이지에서 관리자가 조정 가능
```

### 3.5 분석 파이프라인 통합
```python
async def analyze_pipeline(items: List[ContentItem]) -> List[ContentItem]:
    """수집된 컨텐츠에 대해 키워드 추출 + 감성 분석 + 중요도 산정 실행"""
    keyword_extractor = KeywordExtractor()
    sentiment_analyzer = SentimentAnalyzer()
    importance_scorer = ImportanceScorer()
    
    for item in items:
        # 댓글 전체 텍스트 결합
        all_comments = " ".join([c.body for c in item.comments])
        
        # 키워드 추출 (제목 + 댓글)
        item.keywords = keyword_extractor.extract(item.title + " " + all_comments)
        
        # 감성 분석 (댓글 기반)
        sentiment = sentiment_analyzer.analyze(all_comments)
        item.sentiment = sentiment.label
        item.sentiment_score = sentiment.score
        
        # 개별 댓글 감성 분석
        for comment in item.comments:
            cs = sentiment_analyzer.analyze(comment.body)
            comment.sentiment = cs.label
            comment.sentiment_score = cs.score
        
        # 중요도 산정
        item.importance_score = importance_scorer.score(item)
    
    return items
```

---

## 4. 프론트엔드 상세

### 4.1 API 클라이언트 (lib/api.ts)
```typescript
// fetch 기반 API 클라이언트
// - BASE_URL: 환경변수 NEXT_PUBLIC_API_URL (기본 http://localhost:8000)
// - 공통 에러 핸들링
// - React Query 연동용 쿼리 함수
```

### 4.2 대시보드 (/dashboard)
```
┌─────────────────────────────────────────────────┐
│  Contents Researcher                    [설정]   │
├──────────┬──────────────────────────────────────┤
│          │  📊 수집 현황 요약                      │
│  사이드바  │  ┌──────┬──────┬──────┬──────┐       │
│          │  │유튜브  │인스타 │aggag │ 전체  │       │
│ 대시보드  │  │ 1,234│  567 │  890 │2,691 │       │
│ 컨텐츠   │  └──────┴──────┴──────┴──────┘       │
│ 키워드   │                                       │
│ 스케줄러  │  📈 키워드 트렌드 (최근 7일)            │
│ 설정     │  [Line Chart - 상위 5개 키워드 추이]     │
│          │                                       │
│          │  🔥 최근 수집 컨텐츠 (최신 10개)         │
│          │  [테이블: 제목, 출처, 감성, 중요도, 날짜]  │
│          │                                       │
│          │  ⏱ 수집 스케줄 상태                     │
│          │  [다음 실행 예정 목록]                   │
└──────────┴──────────────────────────────────────┘
```

### 4.3 컨텐츠 검색 (/contents)
```
┌──────────────────────────────────────────────────┐
│  🔍 검색어 입력                          [검색]   │
│                                                  │
│  필터: [출처 ▼] [감성 ▼] [날짜 범위] [정렬 ▼]     │
│                                                  │
│  검색 결과 (총 234건)                              │
│  ┌────────────────────────────────────────────┐  │
│  │ 📺 유튜브 | 제목어쩌구저쩌구...                 │  │
│  │ 키워드: #AI #트렌드 #기술  감성: 긍정 (0.8)    │  │
│  │ 댓글 45개 | 좋아요 1.2K | 중요도: 8.5         │  │
│  │ 2026-04-01                                 │  │
│  ├────────────────────────────────────────────┤  │
│  │ 🌐 aggag | 다른 제목...                      │  │
│  │ ...                                        │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  [< 이전] [1] [2] [3] ... [12] [다음 >]          │
└──────────────────────────────────────────────────┘
```

### 4.4 컨텐츠 상세 (/contents/[id])
```
┌──────────────────────────────────────────────────┐
│  ← 뒤로가기                                      │
│                                                  │
│  📺 유튜브 | 컨텐츠 제목 전체                       │
│  원본 링크: https://...                           │
│  수집일: 2026-04-01 12:00                         │
│                                                  │
│  ┌─────────────────┬────────────────────────┐    │
│  │ 키워드 클라우드   │ 감성 분석 결과           │    │
│  │ [Word Cloud]     │ 긍정: 65% 중립: 25%    │    │
│  │                  │ 부정: 10%              │    │
│  │                  │ 종합: 긍정 (0.72)       │    │
│  └─────────────────┴────────────────────────┘    │
│                                                  │
│  💬 댓글 분석 (45개)                               │
│  [댓글 목록 + 개별 감성 라벨]                       │
└──────────────────────────────────────────────────┘
```

### 4.5 키워드 트렌드 (/keywords)
```
┌──────────────────────────────────────────────────┐
│  📈 키워드 트렌드                                  │
│                                                  │
│  기간: [1주 ▼]  출처: [전체 ▼]                     │
│                                                  │
│  [Line Chart - 선택한 키워드들의 시계열 추이]         │
│                                                  │
│  🔥 급상승 키워드        📊 인기 키워드 TOP 20      │
│  1. AI (▲ 350%)         1. AI (2,345건)          │
│  2. 트렌드 (▲ 120%)     2. 리뷰 (1,890건)         │
│  3. ...                 3. ...                    │
└──────────────────────────────────────────────────┘
```

---

## 5. Docker 구성

### 5.1 docker-compose.yml
```yaml
services:
  db:
    image: timescale/timescaledb:latest-pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: contents_researcher
      POSTGRES_USER: cr_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

### 5.2 .env.example
```
DATABASE_URL=postgresql+asyncpg://cr_user:password@localhost:5432/contents_researcher
REDIS_URL=redis://localhost:6379/0
YOUTUBE_API_KEY=your_youtube_api_key
INSTAGRAM_ACCESS_TOKEN=your_instagram_token
DB_PASSWORD=your_db_password
```

---

## 6. 공통 타입 (shared/types.py)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class ContentItem:
    source: str                          # "youtube", "aggag", "instagram"
    source_url: str                      # 원본 URL
    source_id: str                       # 플랫폼 내 고유 ID
    title: str
    body: Optional[str] = None
    body_hash: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    sentiment: Optional[str] = None      # "positive", "negative", "neutral"
    sentiment_score: Optional[float] = None
    importance_score: Optional[float] = None
    comment_count: int = 0
    like_count: int = 0
    view_count: int = 0
    comments: List['Comment'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    collected_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Comment:
    author: str
    body: str
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    like_count: int = 0

@dataclass
class SentimentResult:
    label: str          # "positive", "negative", "neutral"
    score: float        # -1.0 ~ 1.0
    details: Optional[Dict[str, float]] = None  # {"positive": 0.65, "neutral": 0.25, "negative": 0.10}
```
