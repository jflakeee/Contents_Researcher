"""
수집 스케줄러

APScheduler를 사용하여 플랫폼별 수집 작업을 자동 스케줄링한다.
스케줄 정보는 PostgreSQL에 영속화되어 서버 재시작 후에도 유지된다.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

from shared.constants import DEFAULT_SCHEDULES

logger = logging.getLogger(__name__)


class CollectionScheduler:
    """수집 스케줄러

    APScheduler AsyncIOScheduler를 래핑하여
    수집기 작업의 등록/조회/수정/삭제를 관리한다.
    """

    def __init__(self, database_url: str, timezone: str = "Asia/Seoul"):
        """초기화

        Args:
            database_url: PostgreSQL 연결 문자열 (동기 URL)
            timezone: 스케줄러 시간대
        """
        # asyncpg URL을 psycopg2 URL로 변환 (APScheduler는 동기 DB 드라이버 사용)
        sync_url = database_url.replace("+asyncpg", "").replace("+aiosqlite", "")

        jobstores = {
            "default": SQLAlchemyJobStore(url=sync_url),
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone=timezone,
        )
        self._timezone = timezone

    def start(self) -> None:
        """스케줄러 시작"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("수집 스케줄러 시작 (timezone=%s)", self._timezone)

    def shutdown(self) -> None:
        """스케줄러 종료"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("수집 스케줄러 종료")

    def add_job(
        self,
        job_id: str,
        func: Any,
        cron_expression: str,
        kwargs: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """수집 작업 스케줄 추가

        Args:
            job_id: 작업 고유 ID (예: "collect_youtube")
            func: 실행할 비동기 함수
            cron_expression: cron 표현식 (예: "0 */6 * * *")
            kwargs: 함수에 전달할 키워드 인자

        Returns:
            추가된 작업 정보
        """
        trigger = CronTrigger.from_crontab(cron_expression, timezone=self._timezone)

        job = self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            kwargs=kwargs or {},
            replace_existing=True,
            misfire_grace_time=3600,  # 1시간 이내 지연은 허용
        )

        logger.info("스케줄 추가: id=%s, cron=%s", job_id, cron_expression)
        return self._job_to_dict(job)

    def remove_job(self, job_id: str) -> bool:
        """수집 작업 스케줄 삭제

        Args:
            job_id: 작업 고유 ID

        Returns:
            삭제 성공 여부
        """
        try:
            self._scheduler.remove_job(job_id)
            logger.info("스케줄 삭제: id=%s", job_id)
            return True
        except Exception as e:
            logger.warning("스케줄 삭제 실패: id=%s, error=%s", job_id, str(e))
            return False

    def update_job(
        self,
        job_id: str,
        cron_expression: Optional[str] = None,
        kwargs: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """수집 작업 스케줄 수정

        Args:
            job_id: 작업 고유 ID
            cron_expression: 새 cron 표현식 (None이면 변경 안 함)
            kwargs: 새 키워드 인자 (None이면 변경 안 함)

        Returns:
            수정된 작업 정보 또는 None (실패 시)
        """
        try:
            changes = {}
            if cron_expression:
                changes["trigger"] = CronTrigger.from_crontab(
                    cron_expression, timezone=self._timezone
                )
            if kwargs is not None:
                changes["kwargs"] = kwargs

            job = self._scheduler.modify_job(job_id, **changes)
            logger.info("스케줄 수정: id=%s", job_id)
            return self._job_to_dict(job)

        except Exception as e:
            logger.warning("스케줄 수정 실패: id=%s, error=%s", job_id, str(e))
            return None

    def pause_job(self, job_id: str) -> bool:
        """작업 일시 정지

        Args:
            job_id: 작업 ID

        Returns:
            성공 여부
        """
        try:
            self._scheduler.pause_job(job_id)
            logger.info("스케줄 일시정지: id=%s", job_id)
            return True
        except Exception:
            return False

    def resume_job(self, job_id: str) -> bool:
        """작업 재개

        Args:
            job_id: 작업 ID

        Returns:
            성공 여부
        """
        try:
            self._scheduler.resume_job(job_id)
            logger.info("스케줄 재개: id=%s", job_id)
            return True
        except Exception:
            return False

    def get_jobs(self) -> List[Dict[str, Any]]:
        """등록된 모든 스케줄 조회

        Returns:
            작업 정보 목록
        """
        jobs = self._scheduler.get_jobs()
        return [self._job_to_dict(job) for job in jobs]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """특정 스케줄 조회

        Args:
            job_id: 작업 ID

        Returns:
            작업 정보 또는 None
        """
        job = self._scheduler.get_job(job_id)
        if job:
            return self._job_to_dict(job)
        return None

    @staticmethod
    def _job_to_dict(job) -> Dict[str, Any]:
        """APScheduler Job 객체를 딕셔너리로 변환

        Args:
            job: APScheduler Job

        Returns:
            직렬화 가능한 딕셔너리
        """
        next_run = job.next_run_time
        return {
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
            "trigger": str(job.trigger),
            "pending": job.pending,
        }
