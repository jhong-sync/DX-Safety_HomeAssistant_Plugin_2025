"""
Remote MQTT ingestion adapter stub.

This module provides a stub implementation of AlertIngestPort
for remote MQTT ingestion (dry-run capable).
"""

import asyncio
from typing import AsyncIterator, Dict

class RemoteMqttIngestor:
    """원격 MQTT 수집 어댑터 (스텁)"""
    
    def __init__(self, topic: str):
        """
        초기화합니다.
        
        Args:
            topic: 구독할 MQTT 토픽
        """
        self.topic = topic
    
    async def recv(self) -> AsyncIterator[Dict]:
        """
        원시 경보 데이터를 비동기적으로 수신합니다.
        
        현재는 스텁 구현으로 실제 MQTT 연결 없이 동작합니다.
        
        Yields:
            원시 딕셔너리 데이터
        """
        # Phase 1에서는 실제 MQTT 연결 없이 스텁으로 동작
        while False:  # 실제 구현 시 True로 변경
            yield {}
        
        # 실제 구현 시 제거할 코드
        await asyncio.sleep(0)
        if False:  # 실제 구현 시 조건 변경
            yield {}
