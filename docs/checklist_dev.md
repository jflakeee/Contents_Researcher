# Contents Researcher - 기능별 구현 체크리스트

## Phase 1: 프로젝트 셋업

### 1.1 인프라
- [ ] docker-compose.yml 작성 (PostgreSQL + TimescaleDB + Redis)
- [ ] .env.example 작성
- [ ] .gitignore 작성 (res/, .env, __pycache__, node_modules 등)
- [ ] docker-compose up 정상 기동 확인

### 1.2 백엔드 초기화
- [ ] backend/pyproject.toml 작성 (FastAPI, SQLAlchemy, asyncpg, redis, pydantic-settings)
- [ ] uv init + 의존성 설치
- [ ] app/config.py — pydantic-settings 환경설정
- [ ] app/db/session.py — SQLAlchemy 비동기 엔진/세션
- [ ] app/main.py — FastAPI 앱, CORS, 라우터 등록, lifespan
- [ ] 서버 기동 확인 (uvicorn, Swagger UI 접속)

### 1.3 DB 스키마
- [ ] app/models/content.py — Content 모델
- [ ] app/models/comment.py — Comment 모델
- [ ] app/models/keyword.py — KeywordTrend 모델
- [ ] alembic 초기화 + 비동기 설정
- [ ] 초기 마이그레이션 생성 및 적용
- [ ] TimescaleDB 하이퍼테이블 생성 확인
- [ ] GIN 인덱스, pg_trgm 인덱스 생성 확인

### 1.4 기본 API
- [ ] app/schemas/content.py — ContentSummary, ContentDetail, PaginatedResponse
- [ ] app/schemas/search.py — SearchRequest
- [ ] app/api/contents.py — 검색, 상세, 트렌딩 엔드포인트 (골격)
- [ ] app/api/keywords.py — 인기 키워드, 트렌드 엔드포인트 (골격)
- [ ] app/api/crawler.py — 수집 트리거, 상태 엔드포인트 (골격)
- [ ] app/api/scheduler.py — 스케줄 CRUD 엔드포인트 (골격)
- [ ] Swagger UI에서 전체 API 목록 확인

### 1.5 프론트엔드 초기화
- [ ] pnpm create next-app (App Router, TypeScript, Tailwind)
- [ ] shadcn/ui 초기화 + 기본 컴포넌트 설치
- [ ] src/app/layout.tsx — 루트 레이아웃 (사이드바, 헤더)
- [ ] src/app/dashboard/page.tsx — 대시보드 페이지 (골격)
- [ ] src/app/contents/page.tsx — 컨텐츠 검색 페이지 (골격)
- [ ] src/app/keywords/page.tsx — 키워드 페이지 (골격)
- [ ] src/app/scheduler/page.tsx — 스케줄러 페이지 (골격)
- [ ] src/app/settings/page.tsx — 설정 페이지 (골격)
- [ ] src/lib/api.ts — API 클라이언트
- [ ] src/types/index.ts — TypeScript 타입 정의
- [ ] localhost:3000 접속 확인

### 1.6 공통
- [ ] shared/types.py — ContentItem, Comment, SentimentResult 데이터 클래스
- [ ] shared/constants.py — 출처명, 감성 라벨 등 상수

---

## Phase 2: 수집기 구현

### 2.1 수집기 공통
- [ ] collector/pyproject.toml 작성
- [ ] collector/core/base.py — BaseCollector ABC
- [ ] collector/core/registry.py — CollectorRegistry (플러그인 등록)
- [ ] collector/core/dedup.py — Redis 기반 중복 체크
- [ ] BaseCollector.run() 파이프라인 (수집 → 분석 → 저장) 구현

### 2.2 유튜브 수집기
- [ ] collector/youtube/collector.py — YouTubeCollector
  - [ ] YouTube Data API v3 연동
  - [ ] 키워드 검색 (search.list)
  - [ ] 영상 상세 조회 (videos.list)
  - [ ] 댓글 수집 (commentThreads.list)
  - [ ] API 할당량 추적
- [ ] collector/youtube/parser.py — API 응답 → ContentItem 변환
- [ ] Registry에 YouTubeCollector 등록

### 2.3 aggag.com 수집기
- [ ] collector/aggag/collector.py — AggagCollector
  - [ ] Playwright 브라우저 초기화
  - [ ] 게시글 목록 페이지 스크래핑
  - [ ] 게시글 상세 페이지 스크래핑
  - [ ] 댓글 추출
  - [ ] 페이지네이션 처리
  - [ ] rate limiting (요청 간 딜레이)
- [ ] collector/aggag/parser.py — HTML → ContentItem 변환
- [ ] Registry에 AggagCollector 등록

---

## Phase 3: NLP 파이프라인

### 3.1 키워드 추출
- [ ] analyzer/pyproject.toml 작성
- [ ] analyzer/keywords/extractor.py — KeywordExtractor
  - [ ] 텍스트 전처리 (HTML 태그, 특수문자 제거)
  - [ ] Kiwipiepy 형태소 분석 (명사 추출)
  - [ ] 불용어 제거
  - [ ] KeyBERT 임베딩 기반 상위 N개 키워드 추출
- [ ] analyzer/keywords/keybert_wrapper.py — KeyBERT 래퍼

### 3.2 감성 분석
- [ ] analyzer/sentiment/analyzer.py — SentimentAnalyzer (전략 패턴)
- [ ] analyzer/sentiment/dictionary.py — KNU 감성사전 기반
  - [ ] KNU 사전 로드
  - [ ] 형태소 분석 후 사전 매칭
  - [ ] 부정어 극성 반전
  - [ ] 점수 계산

### 3.3 중요도 산정
- [ ] analyzer/importance/scorer.py — ImportanceScorer
  - [ ] 가중 합산 점수 계산
  - [ ] 정규화 로직
  - [ ] 가중치 설정 가능 구조

### 3.4 분석 파이프라인 통합
- [ ] 수집기의 run() 메서드에서 분석 파이프라인 호출 연동
- [ ] 분석 결과 DB 저장 확인
- [ ] keyword_trends 일별 집계 로직

---

## Phase 4: 프론트엔드 UI

### 4.1 컴포넌트
- [ ] components/layout/Sidebar.tsx — 사이드바 네비게이션
- [ ] components/layout/Header.tsx — 상단 헤더
- [ ] components/search/SearchBar.tsx — 검색 입력
- [ ] components/search/FilterPanel.tsx — 필터 (출처, 감성, 날짜)
- [ ] components/search/ContentCard.tsx — 검색 결과 카드
- [ ] components/charts/TrendLineChart.tsx — 키워드 트렌드 차트
- [ ] components/charts/SentimentPieChart.tsx — 감성 분포 파이차트

### 4.2 페이지 완성
- [ ] /dashboard — 수집 현황 카드, 트렌드 차트, 최근 수집 목록
- [ ] /contents — 검색바, 필터, 결과 카드 목록, 페이지네이션
- [ ] /contents/[id] — 상세 정보, 키워드 클라우드, 감성 분석 결과, 댓글 목록
- [ ] /keywords — 인기 키워드 순위, 급상승 키워드, 트렌드 차트

### 4.3 Playwright E2E 테스트
- [ ] tests/playwright.config.ts — 설정 (baseURL: localhost:3000)
- [ ] tests/dashboard.spec.ts — 대시보드 로드, 데이터 표시 확인
- [ ] tests/contents.spec.ts — 검색 기능, 필터 동작, 페이지네이션
- [ ] tests/search.spec.ts — 검색어 입력 → 결과 표시 → 상세 이동

---

## Phase 5: 스케줄러 + 대시보드 + 추가 수집기

### 5.1 스케줄러
- [ ] collector/core/scheduler.py — APScheduler 설정
  - [ ] SQLAlchemyJobStore (PostgreSQL 영속)
  - [ ] 기본 cron 스케줄 등록
  - [ ] FastAPI lifespan에서 스케줄러 시작/종료
- [ ] /scheduler 페이지 — 스케줄 목록, 추가, 수정, 삭제 UI
- [ ] API: 스케줄 CRUD 엔드포인트 완성

### 5.2 트렌드 대시보드 고도화
- [ ] app/services/trend_service.py — 트렌드 분석 로직
- [ ] /dashboard 차트 데이터 실 연동
- [ ] 급상승 키워드 감지 로직

### 5.3 인스타그램 수집기
- [ ] collector/instagram/collector.py — InstagramCollector
- [ ] collector/instagram/parser.py
- [ ] Registry에 InstagramCollector 등록

---

## Phase 6: 고도화 (추후)

- [ ] LLM(Claude API) 기반 컨텐츠 자동 요약
- [ ] SEO 블로그 글 자동 생성 파이프라인
- [ ] 유사 컨텐츠 추천 기능
- [ ] 트렌드 급상승 알림 (Discord/Slack)
- [ ] ML 기반 감성 분석 (KcELECTRA)
- [ ] 썸네일 키워드 추천
- [ ] /settings 페이지 완성 (API 키 관리, 가중치 조정)
