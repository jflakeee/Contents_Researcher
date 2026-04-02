# Contents Researcher - 종합 구현 계획서

## 1. 프로젝트 개요

### 1.1 목적
인터넷에 작성된 컨텐츠를 자동으로 수집·분류하고, 댓글 분석을 통해 주요 키워드를 추출하여
유튜브 영상 제작 시 활용할 소재를 체계적으로 관리하는 웹 기반 시스템.

### 1.2 핵심 기능
- 멀티 플랫폼 컨텐츠 수집 (유튜브, 인스타그램, aggag.com, SNS)
- 댓글 기반 키워드 추출 및 감성 분석
- 컨텐츠 평가 분류 (긍정/부정/중립)
- 날짜별 자동 수집 스케줄링
- 검색/조회 웹 대시보드

---

## 2. 시스템 아키텍처

### 2.1 전체 구성도

```
┌─────────────┐    ┌─────────────────┐    ┌──────────────┐
│  스케줄러    │───▶│  크롤러/수집기   │───▶│  NLP 분석기  │
│ APScheduler │    │  (플러그인 구조)  │    │ Kiwipiepy    │
└─────────────┘    └─────────────────┘    │ KeyBERT      │
                                           │ KNU 감성사전  │
                                           └──────┬───────┘
                                                  │
                                                  ▼
┌─────────────┐    ┌─────────────────┐    ┌──────────────┐
│ 프론트엔드   │◀───│  백엔드 API     │◀───│  데이터베이스  │
│ Next.js 14  │    │  FastAPI        │    │ PostgreSQL   │
│ shadcn/ui   │    │                 │    │ +TimescaleDB │
└─────────────┘    └─────────────────┘    │ +Redis       │
                                           └──────────────┘
```

### 2.2 아키텍처 선택 근거
- **모노레포**: 크롤러/백엔드/프론트가 긴밀 연동, 공통 타입 공유 용이
- **3-티어 분리**: 수집(Python) → API(Python) → UI(TypeScript) 각 역할 명확
- **플러그인 구조**: BaseCollector 상속으로 새 수집 소스 추가 용이

---

## 3. 기술 스택

### 3.1 백엔드
| 항목 | 기술 | 버전 | 선택 이유 |
|------|------|------|-----------|
| 언어 | Python | 3.12+ | NLP 생태계 최적, 크롤러와 통일 |
| 프레임워크 | FastAPI | 최신 | 비동기, 자동 OpenAPI 문서, Pydantic v2 |
| ORM | SQLAlchemy | 2.0+ | 비동기 지원, 풍부한 생태계 |
| 마이그레이션 | Alembic | 최신 | SQLAlchemy 공식 마이그레이션 도구 |
| 패키지관리 | uv | 최신 | pip 대비 10-100배 빠른 설치 |

### 3.2 프론트엔드
| 항목 | 기술 | 버전 | 선택 이유 |
|------|------|------|-----------|
| 프레임워크 | Next.js | 14+ (App Router) | SSR/SSG, SEO 최적화 |
| UI | shadcn/ui + Tailwind CSS | 최신 | 커스터마이징 자유도, 대시보드 적합 |
| 상태관리 | Zustand or React Query | 최신 | 서버 상태 캐싱 + 경량 |
| 차트 | Recharts | 최신 | React 네이티브, 반응형 차트 |
| 패키지관리 | pnpm | 최신 | 빠른 설치, 디스크 효율 |

### 3.3 크롤러/수집기
| 항목 | 기술 | 선택 이유 |
|------|------|-----------|
| 브라우저 자동화 | Playwright (Python) | 동적 페이지 렌더링, 멀티 브라우저 |
| HTTP 클라이언트 | httpx | 비동기 HTTP, 연결 풀링 |
| HTML 파서 | BeautifulSoup4 | 정적 페이지 경량 파싱 |
| 스케줄링 | APScheduler | cron식 표현, DB 영속 job store |
| API 클라이언트 | google-api-python-client | YouTube Data API v3 |

### 3.4 NLP/분석
| 항목 | 기술 | 선택 이유 |
|------|------|-----------|
| 형태소분석 | Kiwipiepy | Java 불필요, Windows 호환, 빠른 속도 |
| 키워드추출 | KeyBERT | 임베딩 기반 키워드 추출 |
| 감성분석 | KNU 한국어 감성사전 | 규칙 기반으로 빠른 프로토타입 |
| 임베딩 | sentence-transformers | KeyBERT 백엔드 |

### 3.5 인프라
| 항목 | 기술 | 선택 이유 |
|------|------|-----------|
| DB | PostgreSQL 16 + TimescaleDB | 90%+ 압축률, 시계열 최적화 |
| 캐시/큐 | Redis | API 캐싱, 크롤링 큐, 중복 체크 |
| 컨테이너 | Docker Compose | 개발 환경 일괄 구성 |
| 테스트(E2E) | Playwright | workflow_test.txt 요건 |
| 테스트(유닛) | pytest | Python 표준 |

---

## 4. 데이터베이스 스키마

### 4.1 contents (TimescaleDB 하이퍼테이블)
```sql
CREATE TABLE contents (
    id               BIGSERIAL,
    collected_at     TIMESTAMPTZ NOT NULL,       -- 수집 시각
    source           VARCHAR(50) NOT NULL,        -- youtube, instagram, aggag 등
    source_url       TEXT NOT NULL,                -- 원본 URL
    title            TEXT NOT NULL,                -- 컨텐츠 제목
    body             TEXT,                         -- 본문 (선택)
    body_hash        CHAR(64),                     -- SHA-256, 중복 체크용
    keywords         TEXT[],                       -- 추출된 키워드 배열
    sentiment        VARCHAR(10),                  -- positive, negative, neutral
    sentiment_score  FLOAT,                        -- -1.0 ~ 1.0
    importance_score FLOAT,                        -- 중요도 점수
    comment_count    INT DEFAULT 0,
    like_count       INT DEFAULT 0,
    view_count       INT DEFAULT 0,
    metadata         JSONB,                        -- 플랫폼별 추가 데이터
    PRIMARY KEY (collected_at, id)
);

SELECT create_hypertable('contents', 'collected_at');
```

### 4.2 comments
```sql
CREATE TABLE comments (
    id            BIGSERIAL,
    content_id    BIGINT NOT NULL,
    collected_at  TIMESTAMPTZ NOT NULL,
    author        VARCHAR(255),
    body          TEXT NOT NULL,
    sentiment     VARCHAR(10),
    sentiment_score FLOAT,
    like_count    INT DEFAULT 0,
    PRIMARY KEY (collected_at, id)
);

SELECT create_hypertable('comments', 'collected_at');
```

### 4.3 keyword_trends
```sql
CREATE TABLE keyword_trends (
    date          DATE NOT NULL,
    keyword       VARCHAR(100) NOT NULL,
    source        VARCHAR(50),
    count         INT DEFAULT 0,
    avg_sentiment FLOAT,
    PRIMARY KEY (date, keyword, source)
);
```

### 4.4 collection_jobs (수집 작업 이력)
```sql
CREATE TABLE collection_jobs (
    id           BIGSERIAL PRIMARY KEY,
    source       VARCHAR(50) NOT NULL,
    status       VARCHAR(20) NOT NULL,      -- pending, running, completed, failed
    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    items_count  INT DEFAULT 0,
    error_message TEXT,
    metadata     JSONB
);
```

### 4.5 인덱스
```sql
-- 키워드 검색 (GIN)
CREATE INDEX idx_contents_keywords ON contents USING GIN(keywords);

-- 출처별 조회
CREATE INDEX idx_contents_source ON contents(source, collected_at DESC);

-- 감성별 조회
CREATE INDEX idx_contents_sentiment ON contents(sentiment, collected_at DESC);

-- 전문 검색 (pg_trgm)
CREATE INDEX idx_contents_title_trgm ON contents USING GIN(title gin_trgm_ops);

-- 중복 체크
CREATE INDEX idx_contents_body_hash ON contents(body_hash);
```

---

## 5. 디렉토리 구조

```
contents_researcher/
│
├── docs/                              # 기획/설계 문서
│   ├── idea1.txt                      # 원본 아이디어
│   ├── design_overview.md             # 종합 구현 계획 (본 문서)
│   ├── design_detail.md               # 상세 구현 명세
│   ├── checklist_dev.md               # 구현 체크리스트
│   ├── checklist_test.md              # 테스트 체크리스트
│   ├── checklist_decisions.md         # 결정 필요 항목
│   ├── workflow_plan.txt
│   ├── workflow_dev.txt
│   └── workflow_test.txt
│
├── backend/                           # FastAPI 백엔드
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/                       # DB 마이그레이션
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 엔트리포인트
│   │   ├── config.py                  # 환경설정 (pydantic-settings)
│   │   ├── api/                       # API 라우터
│   │   │   ├── __init__.py
│   │   │   ├── contents.py            # 컨텐츠 검색/조회
│   │   │   ├── keywords.py            # 키워드 관련
│   │   │   ├── crawler.py             # 수집 트리거/상태
│   │   │   └── scheduler.py           # 스케줄 관리
│   │   ├── models/                    # SQLAlchemy 모델
│   │   │   ├── __init__.py
│   │   │   ├── content.py
│   │   │   ├── comment.py
│   │   │   └── keyword.py
│   │   ├── schemas/                   # Pydantic 스키마
│   │   │   ├── __init__.py
│   │   │   ├── content.py
│   │   │   └── search.py
│   │   ├── services/                  # 비즈니스 로직
│   │   │   ├── __init__.py
│   │   │   ├── search_service.py
│   │   │   └── trend_service.py
│   │   └── db/                        # DB 연결
│   │       ├── __init__.py
│   │       └── session.py
│   └── tests/
│       ├── __init__.py
│       ├── test_contents_api.py
│       └── test_search_service.py
│
├── collector/                         # 크롤러/수집기
│   ├── pyproject.toml
│   ├── core/                          # 공통 로직
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseCollector ABC
│   │   ├── scheduler.py              # APScheduler 설정
│   │   ├── dedup.py                   # 중복 제거 (Redis Bloom Filter)
│   │   └── registry.py               # 수집기 플러그인 등록
│   ├── youtube/                       # 유튜브 수집기
│   │   ├── __init__.py
│   │   ├── collector.py
│   │   └── parser.py
│   ├── instagram/                     # 인스타그램 수집기
│   │   ├── __init__.py
│   │   ├── collector.py
│   │   └── parser.py
│   ├── aggag/                         # aggag.com 수집기
│   │   ├── __init__.py
│   │   ├── collector.py
│   │   └── parser.py
│   └── tests/
│       ├── __init__.py
│       ├── test_youtube_collector.py
│       └── test_aggag_collector.py
│
├── analyzer/                          # NLP 분석기
│   ├── pyproject.toml
│   ├── keywords/                      # 키워드 추출
│   │   ├── __init__.py
│   │   ├── extractor.py               # 키워드 추출 메인
│   │   └── keybert_wrapper.py         # KeyBERT 래퍼
│   ├── sentiment/                     # 감성 분석
│   │   ├── __init__.py
│   │   ├── analyzer.py                # 감성 분석 메인
│   │   └── dictionary.py             # KNU 사전 기반
│   ├── importance/                    # 중요도 산정
│   │   ├── __init__.py
│   │   └── scorer.py
│   └── tests/
│       ├── __init__.py
│       ├── test_keyword_extractor.py
│       └── test_sentiment_analyzer.py
│
├── frontend/                          # Next.js 프론트엔드
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # 루트 레이아웃
│   │   │   ├── page.tsx               # 홈 → /dashboard 리다이렉트
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   ├── contents/
│   │   │   │   ├── page.tsx           # 검색/조회
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx       # 상세
│   │   │   ├── keywords/
│   │   │   │   └── page.tsx
│   │   │   ├── scheduler/
│   │   │   │   └── page.tsx
│   │   │   └── settings/
│   │   │       └── page.tsx
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui 기본 컴포넌트
│   │   │   ├── search/                # 검색 관련
│   │   │   ├── charts/                # 차트 컴포넌트
│   │   │   └── layout/                # 레이아웃 (사이드바, 헤더)
│   │   ├── lib/
│   │   │   ├── api.ts                 # API 클라이언트
│   │   │   └── utils.ts
│   │   └── types/
│   │       └── index.ts               # TypeScript 타입 정의
│   └── tests/                         # Playwright E2E
│       ├── playwright.config.ts
│       ├── dashboard.spec.ts
│       ├── contents.spec.ts
│       └── search.spec.ts
│
├── shared/                            # 공유 리소스
│   ├── __init__.py
│   ├── types.py                       # 공통 데이터 타입
│   └── constants.py                   # 상수 정의
│
├── docker-compose.yml                 # PostgreSQL + TimescaleDB + Redis
├── .env.example                       # 환경변수 템플릿
├── .gitignore                         # res/ 포함
├── RESUME.md                          # 진행 현황
└── README.md                          # 사용법
```

---

## 6. API 설계

### 6.1 엔드포인트 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/contents/search` | 컨텐츠 검색 (필터, 키워드, 날짜 범위) |
| GET | `/api/v1/contents/{id}` | 컨텐츠 상세 조회 |
| GET | `/api/v1/contents/trending` | 트렌드 컨텐츠 목록 |
| GET | `/api/v1/contents/{id}/comments` | 컨텐츠별 댓글 목록 |
| GET | `/api/v1/keywords/top` | 인기 키워드 (기간, 출처 필터) |
| GET | `/api/v1/keywords/trend` | 키워드 트렌드 (시계열) |
| GET | `/api/v1/sources/stats` | 출처별 수집 통계 |
| POST | `/api/v1/crawler/trigger` | 수동 수집 트리거 |
| GET | `/api/v1/crawler/status` | 현재 수집 상태 |
| GET | `/api/v1/crawler/history` | 수집 이력 |
| GET | `/api/v1/scheduler/jobs` | 스케줄 목록 |
| POST | `/api/v1/scheduler/jobs` | 스케줄 추가 |
| PUT | `/api/v1/scheduler/jobs/{id}` | 스케줄 수정 |
| DELETE | `/api/v1/scheduler/jobs/{id}` | 스케줄 삭제 |

### 6.2 검색 요청 스키마 예시
```json
{
  "query": "키워드 검색어",
  "sources": ["youtube", "aggag"],
  "sentiment": "positive",
  "date_from": "2026-03-01",
  "date_to": "2026-04-01",
  "sort_by": "importance_score",
  "sort_order": "desc",
  "page": 1,
  "page_size": 20
}
```

---

## 7. 구현 우선순위 (Phase별)

| Phase | 내용 | 주요 산출물 |
|-------|------|------------|
| 1 | 프로젝트 셋업 + Docker + DB 스키마 + 기본 API + 프론트 골격 | docker-compose.yml, DB 마이그레이션, API 골격, Next.js 골격 |
| 2 | 유튜브 수집기 + aggag.com 수집기 | BaseCollector, YouTubeCollector, AggagCollector |
| 3 | NLP 파이프라인 (키워드 추출 + 감성 분석) | KeywordExtractor, SentimentAnalyzer |
| 4 | 프론트엔드 검색/조회 UI + Playwright 테스트 | /contents 페이지, 검색 UI, E2E 테스트 |
| 5 | 스케줄러 + 트렌드 대시보드 + 인스타그램 수집기 | /dashboard, /scheduler, InstagramCollector |
| 6 | LLM 요약 + SEO 블로그 + 고도화 | Claude API 연동, SEO 파이프라인 |

---

## 8. 추가 아이디어 (Phase 6+)

- 트렌드 급상승 키워드 자동 알림 (Discord/Slack 웹훅)
- LLM(Claude API) 기반 컨텐츠 자동 요약
- 유사 컨텐츠 추천 (TF-IDF 코사인 유사도)
- SEO 블로그 글 자동 생성 파이프라인
- 썸네일 키워드 추천
- 플랫폼 간 동일 키워드 크로스 분석
