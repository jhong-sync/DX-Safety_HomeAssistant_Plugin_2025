"""
Metrics port interface.

This module defines the protocol for metrics collection.
"""

from typing import Protocol

class MetricsPort(Protocol):
    """메트릭 수집 포트 인터페이스"""
    
    def increment_counter(self, name: str, value: int = 1, labels: dict = None) -> None:
        """
        카운터를 증가시킵니다.
        
        Args:
            name: 메트릭 이름
            value: 증가값
            labels: 라벨
        """
        ...
    
    def record_histogram(self, name: str, value: float, labels: dict = None) -> None:
        """
        히스토그램을 기록합니다.
        
        Args:
            name: 메트릭 이름
            value: 기록할 값
            labels: 라벨
        """
        ...
    
    def set_gauge(self, name: str, value: float, labels: dict = None) -> None:
        """
        게이지를 설정합니다.
        
        Args:
            name: 메트릭 이름
            value: 설정할 값
            labels: 라벨
        """
        ...
