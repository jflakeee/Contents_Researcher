# Contents Researcher - 진행 현황

## 현재 단계: Phase 1~5 구현 완료

## 완료 항목

### 기획 (2026-04-02)
- [x] 아이디어 정리 (docs/idea1.txt)
- [x] 워크플로우 정의 (docs/workflow_plan.txt, workflow_dev.txt, workflow_test.txt)
- [x] 유튜브 컨텐츠 제작 팀 구성 정리

### 설계 (2026-04-02)
- [x] 종합 구현 계획서 (docs/design_overview.md)
- [x] 상세 구현 명세서 (docs/design_detail.md)
- [x] 구현 체크리스트 (docs/checklist_dev.md)
- [x] 테스트 체크리스트 (docs/checklist_test.md)
- [x] 결정 항목 체크리스트 (docs/checklist_decisions.md)

### Phase 1: 프로젝트 셋업 (2026-04-02)
- [x] docker-compose.yml (PostgreSQL + TimescaleDB + Redis)
- [x] .env.example, .gitignore
- [x] 백엔드 FastAPI 초기화 (main.py, config.py, DB 세션)
- [x] SQLAlchemy 모델 (Content, Comment, KeywordTrend, CollectionJob)
- [x] Pydantic 스키마 (ContentSummary, ContentDetail, SearchRequest 등)
- [x] API 라우터 4개 (contents, keywords, crawler, scheduler)
- [x] 서비스 레이어 (SearchService, TrendService)
- [x] Alembic 마이그레이션 설정
- [x] 프론트엔드 Next.js 14 초기화 (shadcn/ui, Tailwind)
- [x] API 클라이언트, TypeScript 타입, 유틸리티
- [x] 공통 타입/상수 (shared/types.py, constants.py)
- [x] next.config.ts API 프록시 설정

### Phase 2: 수집기 (2026-04-02)
- [x] BaseCollector 추상 클래스 + 플러그인 레지스트리
- [x] 중복 제거 모듈 (Redis 기반)
- [x] YouTubeCollector (Data API v3, 할당량 관리)
- [x] AggagCollector (Playwright 스크래핑)

### Phase 3: NLP 파이프라인 (2026-04-02)
- [x] KeywordExtractor (Kiwipiepy + KeyBERT)
- [x] SentimentAnalyzer (KNU 감성사전 기반, 전략 패턴)
- [x] ImportanceScorer (가중 합산, 로그 정규화)
- [x] AnalysisPipeline (통합 파이프라인)

### Phase 4: 프론트엔드 UI + 테스트 (2026-04-02)
- [x] Sidebar 네비게이션 컴포넌트
- [x] 대시보드 페이지 (/dashboard) — 수집 현황, 트렌드 차트, 최근 수집 목록
- [x] 컨텐츠 검색 페이지 (/contents) — 검색, 필터, 페이지네이션
- [x] 컨텐츠 상세 페이지 (/contents/[id]) — 키워드, 감성 분석, 댓글
- [x] 키워드 트렌드 페이지 (/keywords) — 차트, TOP 20
- [x] 스케줄러 페이지 (/scheduler) — 스케줄 CRUD, 수동 수집, 이력
- [x] 설정 페이지 (/settings) — API 키, 수집 주기, 분석 설정, 가중치
- [x] Playwright E2E 테스트 (dashboard, contents, search)

### Phase 5: 스케줄러 + 인스타그램 (2026-04-02)
- [x] CollectionScheduler (APScheduler + PostgreSQL 영속)
- [x] InstagramCollector (Playwright 스크래핑)

### 테스트 코드 (2026-04-02)
- [x] test_youtube_collector.py (파서 테스트)
- [x] test_aggag_collector.py (파서 테스트)
- [x] test_keyword_extractor.py
- [x] test_sentiment_analyzer.py
- [x] test_contents_api.py (백엔드 API 테스트)
- [x] test_search_service.py
- [x] Playwright E2E: dashboard.spec.ts, contents.spec.ts, search.spec.ts

## 미완료 (Phase 6 — 추후)

- [ ] LLM(Claude API) 기반 컨텐츠 자동 요약
- [ ] SEO 블로그 글 자동 생성 파이프라인
- [ ] 유사 컨텐츠 추천 기능
- [ ] ML 기반 감성 분석 (KcELECTRA)
- [ ] 썸네일 키워드 추천

## 주요 결정 사항

| 항목 | 결정 |
|------|------|
| 아키텍처 | 모노레포 3-티어 |
| 백엔드 | Python 3.12 + FastAPI |
| 프론트 | Next.js 14 + shadcn/ui + Tailwind CSS |
| DB | PostgreSQL 16 + TimescaleDB + Redis |
| NLP | Kiwipiepy + KeyBERT + KNU 감성사전 |
| 수집 | YouTube Data API + Playwright (aggag, 인스타) |
| 인프라 | Docker Compose |
| 테스트 | Playwright (E2E) + pytest (유닛) |
| 인증 | 없음 (팀 내부용) |
| 언어 | 한국어 전용 |
| Git | GitHub |
| 배포 | 로컬 우선 |

## 실행 방법

```bash
# 1. 인프라 기동
docker-compose up -d

# 2. 백엔드 실행
cd backend
uv sync
uvicorn app.main:app --reload

# 3. 프론트엔드 실행
cd frontend
pnpm install
pnpm dev

# 4. 접속
# 프론트엔드: http://localhost:3000
# 백엔드 API: http://localhost:8000
# Swagger UI: http://localhost:8000/docs
```

## 파일 구조 (108개 소스 파일)

```
contents_researcher/
├── docs/              (9 files) — 기획/설계 문서
├── backend/           (26 files) — FastAPI 백엔드
│   ├── app/api/       — 4개 API 라우터
│   ├── app/models/    — SQLAlchemy 모델
│   ├── app/schemas/   — Pydantic 스키마
│   ├── app/services/  — 비즈니스 로직
│   ├── alembic/       — DB 마이그레이션
│   └── tests/         — pytest 유닛 테스트
├── collector/         (14 files) — 크롤러/수집기
│   ├── core/          — BaseCollector, 레지스트리, 중복제거, 스케줄러
│   ├── youtube/       — YouTube Data API v3
│   ├── aggag/         — Playwright 스크래핑
│   ├── instagram/     — Playwright 스크래핑
│   └── tests/         — 수집기 테스트
├── analyzer/          (10 files) — NLP 분석기
│   ├── keywords/      — Kiwipiepy + KeyBERT
│   ├── sentiment/     — KNU 감성사전
│   ├── importance/    — 가중 합산 중요도
│   └── tests/         — 분석기 테스트
├── frontend/          (40+ files) — Next.js 프론트엔드
│   ├── src/app/       — 7개 페이지
│   ├── src/components/— shadcn/ui + Sidebar
│   ├── src/lib/       — API 클라이언트, 유틸리티
│   └── tests/         — Playwright E2E
├── shared/            (3 files) — 공통 타입/상수
├── docker-compose.yml
├── .env.example
├── .gitignore
└── RESUME.md
```
