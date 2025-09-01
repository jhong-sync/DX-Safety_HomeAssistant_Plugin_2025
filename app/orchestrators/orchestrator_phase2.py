"""
Phase 2 orchestrator for DX-Safety.

This module implements the main orchestrator for Phase 2,
with reliability features including idempotency and outbox pattern.
"""

import asyncio
import hashlib
from typing import AsyncIterator, Dict
from app.core import normalize, policy
from app.core.models import CAE
from app.adapters.storage.sqlite_idem import SQLiteIdemStore
from app.adapters.storage.sqlite_outbox import SQLiteOutbox
from app.adapters.mqtt_local.publisher_async import LocalMqttPublisher
from app.ports.ingest import AlertIngestPort

class OrchestratorP2:
    """Phase 2 오케스트레이터 (신뢰성 기능 포함)"""
    
    def __init__(self, 
                 ingest: AlertIngestPort, 
                 publisher: LocalMqttPublisher, 
                 idem: SQLiteIdemStore,
                 *,
                 severity_threshold: str,
                 queue_maxsize: int = 1000,
                 drop_on_full: bool = False):
        """
        초기화합니다.
        
        Args:
            ingest: 경보 수집 포트
            publisher: MQTT 발송 어댑터
            idem: Idempotency 저장소
            severity_threshold: 심각도 임계값
            queue_maxsize: 큐 최대 크기
            drop_on_full: 큐가 가득 찰 때 메시지 드롭 여부
        """
        self.ingest = ingest
        self.publisher = publisher
        self.idem = idem
        self.q = asyncio.Queue(maxsize=queue_maxsize)
        self.drop_on_full = drop_on_full
        self.threshold = severity_threshold
    
    async def start(self) -> None:
        """
        오케스트레이터를 시작합니다.
        
        수집 -> 큐 -> 정규화 -> 정책 -> 중복제거 -> 발송의 파이프라인을 실행합니다.
        """
        # Idempotency 저장소 초기화
        await self.idem.init()
        
        # 프로듀서, 컨슈머, 발송 워커 태스크 생성
        prod = asyncio.create_task(self._producer())
        pubw = asyncio.create_task(self.publisher.start())
        cons = asyncio.create_task(self._consumer())
        
        # 모든 태스크 완료 대기
        await asyncio.gather(prod, cons, pubw)
    
    async def _producer(self):
        """원시 데이터를 큐에 추가하는 프로듀서"""
        async for raw in self.ingest.recv():
            try:
                self.q.put_nowait(raw)
            except asyncio.QueueFull:
                if self.drop_on_full:
                    # 큐가 가득 찰 때 메시지 드롭
                    continue
                else:
                    # 큐가 가득 찰 때 블록
                    await self.q.put(raw)
    
    async def _consumer(self):
        """큐에서 데이터를 소비하는 컨슈머"""
        while True:
            raw = await self.q.get()
            
            try:
                # 정규화
                cae: CAE = normalize.to_cae(raw)
                
                # 중복 제거를 위한 키 생성
                key = hashlib.sha256(f"{cae.event_id}:{cae.sent_at}".encode()).hexdigest()
                
                # Idempotency 체크
                if not await self.idem.add_if_absent(key):
                    # 중복 메시지, 건너뛰기
                    continue
                
                # 정책 평가
                dec = policy.evaluate(cae, threshold=self.threshold)
                
                # 트리거된 경우에만 발송
                if dec.trigger:
                    await self.publisher.enqueue_json(f"alerts/{dec.level}", {
                        "id": cae.event_id,
                        "sentAt": cae.sent_at,
                        "headline": cae.headline,
                        "severity": dec.level,
                        "reason": dec.reason
                    })
                    
            except Exception as e:
                # 오류 처리 (로깅만 하고 계속 진행)
                import logging
                logging.error(f"메시지 처리 오류: {e}")
                continue
