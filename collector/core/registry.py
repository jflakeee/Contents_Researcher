"""
수집기 플러그인 레지스트리

새 수집기를 등록/조회하는 중앙 관리 모듈.
수집기 추가 시 register()로 등록하면 API에서 자동으로 사용 가능하다.
"""

import logging
from typing import Dict, Optional, Type

from collector.core.base import BaseCollector

logger = logging.getLogger(__name__)


class CollectorRegistry:
    """수집기 등록/조회 레지스트리

    싱글톤 패턴으로 전역에서 하나의 레지스트리를 공유한다.
    """

    _instance: Optional["CollectorRegistry"] = None
    _collectors: Dict[str, BaseCollector]

    def __new__(cls) -> "CollectorRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._collectors = {}
        return cls._instance

    def register(self, name: str, collector: BaseCollector) -> None:
        """수집기 인스턴스 등록

        Args:
            name: 수집기 이름 (예: "youtube", "aggag")
            collector: BaseCollector 인스턴스
        """
        self._collectors[name] = collector
        logger.info("수집기 등록: %s (%s)", name, type(collector).__name__)

    def register_class(self, name: str, collector_class: Type[BaseCollector], **kwargs) -> None:
        """수집기 클래스를 인스턴스화하여 등록

        Args:
            name: 수집기 이름
            collector_class: BaseCollector 하위 클래스
            **kwargs: 생성자에 전달할 인자
        """
        instance = collector_class(**kwargs)
        self.register(name, instance)

    def get(self, name: str) -> Optional[BaseCollector]:
        """등록된 수집기 조회

        Args:
            name: 수집기 이름

        Returns:
            수집기 인스턴스 또는 None
        """
        collector = self._collectors.get(name)
        if collector is None:
            logger.warning("등록되지 않은 수집기: %s", name)
        return collector

    def list_all(self) -> Dict[str, BaseCollector]:
        """등록된 모든 수집기 조회

        Returns:
            {이름: 수집기 인스턴스} 딕셔너리
        """
        return dict(self._collectors)

    def list_names(self) -> list[str]:
        """등록된 수집기 이름 목록

        Returns:
            수집기 이름 리스트
        """
        return list(self._collectors.keys())

    def clear(self) -> None:
        """모든 수집기 등록 해제 (테스트용)"""
        self._collectors.clear()
        logger.info("모든 수집기 등록 해제")
