"""
Alert dispatch port interface.

This module defines the protocol for alert dispatch.
"""

from typing import Protocol
from app.core.models import CAE, Decision

class AlertDispatchPort(Protocol):
    """경보 발송 포트 인터페이스"""
    
    async def publish_alert(self, cae: CAE, decision: Decision) -> None:
        """
        경보를 발송합니다.
        
        Args:
            cae: 경보 데이터
            decision: 정책 평가 결과
        """
        ...
