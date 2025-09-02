"""
Phase 3 orchestrator for DX-Safety.

This module implements the main orchestrator for Phase 3,
with observability features including metrics and structured logging.
"""

import asyncio
import hashlib
import time
from typing import AsyncIterator, Dict
from app.core import normalize, policy
from app.core.models import CAE
from app.adapters.storage.sqlite_idem import SQLiteIdemStore
from app.adapters.storage.sqlite_outbox import SQLiteOutbox
from app.adapters.mqtt_local.publisher_async import LocalMqttPublisher
from app.ports.ingest import AlertIngestPort
from app.observability import metrics
from app.observability.logging_setup import get_logger

log = get_logger("dxsafety.orchestrator_phase3")

class OrchestratorP3:
    """Phase 3 오케스트레이터 (관측성 기능 포함)"""
    
    def __init__(self, 
                 ingest: AlertIngestPort, 
                 publisher: LocalMqttPublisher, 
                 idem: SQLiteIdemStore,
                 *,
                 severity_threshold: str,
                 queue_maxsize: int = 1000):
        """
        초기화합니다.
        
        Args:
            ingest: 경보 수집 포트
            publisher: MQTT 발송 어댑터
            idem: Idempotency 저장소
            severity_threshold: 심각도 임계값
            queue_maxsize: 큐 최대 크기
        """
        self.ingest = ingest
        self.publisher = publisher
        self.idem = idem
        self.q = asyncio.Queue(maxsize=queue_maxsize)
        self.threshold = severity_threshold
        
        # 시작 시간 기록
        self.start_time = time.time()
        
        log.info("Phase 3 오케스트레이터 초기화됨")
    
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
        
        # 메트릭 업데이트 태스크
        metrics_task = asyncio.create_task(self._update_metrics())
        
        log.info("Phase 3 오케스트레이터 시작됨")
        
        # 모든 태스크 완료 대기
        await asyncio.gather(prod, cons, pubw, metrics_task)
    
    async def _producer(self):
        """원시 데이터를 큐에 추가하는 프로듀서"""
        async for raw in self.ingest.recv():
            # 메트릭 업데이트
            metrics.alerts_received.labels(source="mqtt").inc()
            
            try:
                self.q.put_nowait(raw)
                # 큐 깊이 메트릭 업데이트
                metrics.queue_depth.set(self.q.qsize())
            except asyncio.QueueFull:
                log.warning("큐가 가득 찼습니다. 메시지를 드롭합니다.")
                continue
    
    async def _consumer(self):
        """큐에서 데이터를 소비하는 컨슈머"""
        while True:
            raw = await self.q.get()
            
            try:
                # 전체 처리 시간 측정 시작
                t0 = time.perf_counter()
                
                # 정규화 (시간 측정)
                with metrics.normalize_seconds.time():
                    cae: CAE = normalize.to_cae(raw)
                
                # 유효한 경보 메트릭 증가
                metrics.alerts_valid.labels(severity=cae.severity).inc()
                
                # 중복 제거를 위한 키 생성
                key = hashlib.sha256(f"{cae.event_id}:{cae.sent_at}".encode()).hexdigest()
                
                # Idempotency 체크
                if not await self.idem.add_if_absent(key):
                    # 중복 메시지, 건너뛰기
                    metrics.alerts_duplicate.inc()
                    log.info("중복 메시지 필터링됨", event_id=cae.event_id)
                    continue
                
                # 정책 평가 (시간 측정)
                with metrics.policy_seconds.time():
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
                    
                    # 트리거된 경보 메트릭 증가
                    metrics.alerts_triggered.labels(
                        severity=cae.severity,
                        level=dec.level
                    ).inc()
                    
                    log.info(f"경보 발송됨 event_id:{cae.event_id} severity:{cae.severity} level:{dec.level} reason:{dec.reason}")
                
                # 전체 처리 시간 측정
                total_time = time.perf_counter() - t0
                metrics.end_to_end_seconds.observe(total_time)
                
            except Exception as e:
                log.error(f"메시지 처리 오류 error:{str(e)} event_id:{raw.get('id', 'unknown')}")
                continue
    
    async def _update_metrics(self):
        """주기적으로 메트릭을 업데이트합니다."""
        while True:
            try:
                # 업타임 메트릭 업데이트
                uptime = time.time() - self.start_time
                metrics.uptime_seconds.set(uptime)
                
                # 저장소 크기 메트릭 업데이트
                idem_count = await self.idem.get_count()
                metrics.idem_store_size.set(idem_count)
                
                # Outbox 크기 메트릭 업데이트 (publisher에서 가져오기)
                if hasattr(self.publisher, 'outbox'):
                    outbox_count = await self.publisher.outbox.get_count()
                    metrics.outbox_size.set(outbox_count)
                
                await asyncio.sleep(30)  # 30초마다 업데이트
                
            except Exception as e:
                log.error(f"메트릭 업데이트 오류 error:{str(e)}")
                await asyncio.sleep(30)
