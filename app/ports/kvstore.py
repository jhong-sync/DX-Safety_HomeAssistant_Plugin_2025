"""
Key-value store port interface.

This module defines the protocol for key-value storage.
"""

from typing import Protocol, Optional

class KVStorePort(Protocol):
    """키-값 저장소 포트 인터페이스"""
    
    async def get(self, key: str) -> Optional[str]:
        """
        키로 값을 조회합니다.
        
        Args:
            key: 조회할 키
            
        Returns:
            값 또는 None
        """
        ...
    
    async def set(self, key: str, value: str, ttl_sec: Optional[int] = None) -> None:
        """
        키-값을 저장합니다.
        
        Args:
            key: 저장할 키
            value: 저장할 값
            ttl_sec: TTL (초), None이면 만료 없음
        """
        ...
    
    async def delete(self, key: str) -> None:
        """
        키를 삭제합니다.
        
        Args:
            key: 삭제할 키
        """
        ...
