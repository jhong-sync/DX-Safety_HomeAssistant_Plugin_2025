"""
Phase 1 orchestrator for DX-Safety.

This module implements the main orchestrator for Phase 1,
connecting ingest, normalize, policy, and dry-run dispatch.
"""

import asyncio
from typing import Optional, AsyncIterator, Dict
from app.core import normalize, policy
from app.core.models import CAE
from app.ports.ingest import AlertIngestPort
from app.ports.dispatch import AlertDispatchPort

class OrchestratorP1:
    """Phase 1 오케스트레이터"""
    
    def __init__(self, 
                 ingest: AlertIngestPort, 
                 dispatch: AlertDispatchPort, 
                 *, 
                 severity_threshold: str = "moderate"):
        """
        초기화합니다.
        
        Args:
            ingest: 경보 수집 포트
            dispatch: 경보 발송 포트
            severity_threshold: 심각도 임계값
        """
        self.ingest = ingest
        self.dispatch = dispatch
        self.threshold = severity_threshold
    
    async def start(self) -> None:
        """
        오케스트레이터를 시작합니다.
        
        수집 -> 정규화 -> 정책 평가 -> 발송의 파이프라인을 실행합니다.
        """
        async for raw in self._stream():
            # 정규화
            cae: CAE = normalize.to_cae(raw)
            
            # 정책 평가
            dec = policy.evaluate(cae, threshold=self.threshold)
            
            # 트리거된 경우에만 발송
            if dec.trigger:
                await self.dispatch.publish_alert(cae, dec)
    
    async def _stream(self) -> AsyncIterator[Dict]:
        """
        원시 데이터 스트림을 생성합니다.
        
        Yields:
            원시 딕셔너리 데이터
        """
        async for msg in self.ingest.recv():
            yield msg
