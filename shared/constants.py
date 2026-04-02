"""
공통 상수 정의

전체 프로젝트에서 사용하는 상수값.
하드코딩 방지를 위해 모든 고정값은 여기에서 관리한다.
"""

# === 수집 출처 ===
SOURCE_YOUTUBE = "youtube"
SOURCE_INSTAGRAM = "instagram"
SOURCE_AGGAG = "aggag"

# 지원하는 모든 출처 목록
ALL_SOURCES = [SOURCE_YOUTUBE, SOURCE_INSTAGRAM, SOURCE_AGGAG]

# 출처별 표시명 (한국어)
SOURCE_DISPLAY_NAMES = {
    SOURCE_YOUTUBE: "유튜브",
    SOURCE_INSTAGRAM: "인스타그램",
    SOURCE_AGGAG: "aggag",
}

# === 감성 분류 ===
SENTIMENT_POSITIVE = "positive"
SENTIMENT_NEGATIVE = "negative"
SENTIMENT_NEUTRAL = "neutral"

ALL_SENTIMENTS = [SENTIMENT_POSITIVE, SENTIMENT_NEGATIVE, SENTIMENT_NEUTRAL]

# 감성 한국어 라벨
SENTIMENT_DISPLAY_NAMES = {
    SENTIMENT_POSITIVE: "긍정",
    SENTIMENT_NEGATIVE: "부정",
    SENTIMENT_NEUTRAL: "중립",
}

# === 수집 작업 상태 ===
JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"

# === 기본 설정값 ===
# 키워드 추출 기본 개수
DEFAULT_KEYWORDS_COUNT = 15

# 감성 분류 기본 임계값
DEFAULT_SENTIMENT_THRESHOLD = 0.1

# 기본 페이지 크기
DEFAULT_PAGE_SIZE = 20

# 중요도 가중치 기본값
DEFAULT_IMPORTANCE_WEIGHTS = {
    "comment_count": 0.25,
    "like_count": 0.20,
    "sentiment_bias": 0.15,
    "keyword_relevance": 0.25,
    "recency": 0.15,
}

# === 수집 주기 기본값 (cron 표현식) ===
DEFAULT_SCHEDULES = {
    SOURCE_YOUTUBE: "0 */6 * * *",      # 6시간마다
    SOURCE_AGGAG: "0 */3 * * *",        # 3시간마다
    SOURCE_INSTAGRAM: "0 0,12 * * *",   # 하루 2회 (0시, 12시)
}

# 키워드 트렌드 집계 스케줄
KEYWORD_TREND_SCHEDULE = "0 0 * * *"  # 매일 자정
