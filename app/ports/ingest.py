"""
Alert ingestion port interface.

This module defines the protocol for alert ingestion.
"""

from typing import AsyncIterator, Protocol, Any

class AlertIngestPort(Protocol):
    """경보 수집 포트 인터페이스"""
    
    async def recv(self) -> AsyncIterator[dict]:
        """
        원시 경보 데이터를 비동기적으로 수신합니다.
        
        Yields:
            원시 딕셔너리 데이터
        """
        ...
