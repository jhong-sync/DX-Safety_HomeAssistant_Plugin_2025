"""
Phase 5 orchestrator for DX-Safety.

This module implements the main orchestrator for Phase 5,
with TTS voice notifications and Home Assistant integration.
"""

import asyncio
import hashlib
import time
from typing import AsyncIterator, Dict, Optional, Tuple
from app.core import normalize
from app.core.models import CAE, Decision
from app.core.geo_policy import evaluate_geographic_policy, evaluate_simple_policy
from app.core.voice_template import create_voice_message
from app.adapters.storage.sqlite_idem import SQLiteIdemStore
from app.adapters.storage.sqlite_outbox import SQLiteOutbox
from app.adapters.mqtt_local.publisher_async import LocalMqttPublisher
from app.adapters.homeassistant.client import HAClient
from app.adapters.tts.engine import TTSEngine
from app.ports.ingest import AlertIngestPort
from app.observability import metrics
from app.observability.logging_setup import get_logger

log = get_logger()

class OrchestratorP5:
    """Phase 5 오케스트레이터 (TTS & 음성 알림)"""
    
    def __init__(self, 
                 ingest: AlertIngestPort, 
                 publisher: LocalMqttPublisher, 
                 idem: SQLiteIdemStore,
                 ha_client: HAClient,
                 tts_engine: TTSEngine,
                 *,
                 severity_threshold: str,
                 distance_threshold_km: float = 5.0,
                 polygon_buffer_km: float = 0.0,
                 policy_mode: str = "AND",
                 voice_enabled: bool = True,
                 voice_language: str = "ko-KR",
                 queue_maxsize: int = 1000):
        """
        초기화합니다.
        
        Args:
            ingest: 경보 수집 포트
            publisher: MQTT 발송 어댑터
            idem: Idempotency 저장소
            ha_client: Home Assistant 클라이언트
            tts_engine: TTS 엔진
            severity_threshold: 심각도 임계값
            distance_threshold_km: 거리 임계값 (킬로미터)
            polygon_buffer_km: 폴리곤 버퍼 (킬로미터)
            policy_mode: 정책 모드 ("AND" 또는 "OR")
            voice_enabled: 음성 알림 활성화 여부
            voice_language: 음성 언어 코드
            queue_maxsize: 큐 최대 크기
        """
        self.ingest = ingest
        self.publisher = publisher
        self.idem = idem
        self.ha_client = ha_client
        self.tts_engine = tts_engine
        self.q = asyncio.Queue(maxsize=queue_maxsize)
        self.threshold = severity_threshold
        self.distance_threshold = distance_threshold_km
        self.polygon_buffer = polygon_buffer_km
        self.policy_mode = policy_mode
        self.voice_enabled = voice_enabled
        self.voice_language = voice_language
        
        # 홈 좌표 캐시
        self.home_coordinates: Optional[Tuple[float, float]] = None
        
        # 시작 시간 기록
        self.start_time = time.time()
        
        log.info("오케스트레이터 초기화됨")
    
    async def start(self) -> None:
        """
        오케스트레이터를 시작합니다.
        
        수집 -> 큐 -> 정규화 -> 지리적정책 -> 중복제거 -> 발송 -> 음성알림의 파이프라인을 실행합니다.
        """
        # Idempotency 저장소 초기화
        await self.idem.init()
        
        # 홈 좌표 가져오기
        await self._load_home_coordinates()
        
        # TTS 엔진 시작
        if self.voice_enabled:
            tts_task = asyncio.create_task(self.tts_engine.start())
        
        # 프로듀서, 컨슈머, 발송 워커 태스크 생성
        prod = asyncio.create_task(self._producer())
        pubw = asyncio.create_task(self.publisher.start())
        cons = asyncio.create_task(self._consumer())
        
        # 메트릭 업데이트 태스크
        metrics_task = asyncio.create_task(self._update_metrics())
        
        log.info("Phase 5 오케스트레이터 시작됨")
        
        # 모든 태스크 완료 대기
        if self.voice_enabled:
            await asyncio.gather(prod, cons, pubw, metrics_task, tts_task)
        else:
            await asyncio.gather(prod, cons, pubw, metrics_task)
    
    async def _load_home_coordinates(self) -> None:
        """Home Assistant에서 홈 좌표를 가져옵니다."""
        try:
            async with self.ha_client as client:
                coords = await client.get_zone_home()
                if coords:
                    self.home_coordinates = coords
                    log.info("홈 좌표 로드됨", 
                            lat=coords[0], 
                            lon=coords[1])
                else:
                    log.warning("홈 좌표를 가져올 수 없습니다. 지리적 정책이 비활성화됩니다.")
        except Exception as e:
            log.error("홈 좌표 로드 실패", error=str(e))
    
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
                    log.debug("중복 메시지 필터링됨", event_id=cae.event_id)
                    continue
                
                # 지리적 정책 평가 (시간 측정)
                with metrics.policy_seconds.time():
                    if self.home_coordinates:
                        # 지리적 정책 평가
                        dec = evaluate_geographic_policy(
                            cae,
                            home_coordinates=self.home_coordinates,
                            severity_threshold=self.threshold,
                            distance_threshold_km=self.distance_threshold,
                            polygon_buffer_km=self.polygon_buffer,
                            mode=self.policy_mode
                        )
                    else:
                        # 단순 정책 평가 (지리적 고려 없음)
                        dec = evaluate_simple_policy(
                            cae,
                            severity_threshold=self.threshold
                        )
                
                # 트리거된 경우에만 발송 및 음성 알림
                if dec.trigger:
                    # MQTT 발송
                    await self.publisher.enqueue_json(f"alerts/{dec.level}", {
                        "id": cae.event_id,
                        "sentAt": cae.sent_at,
                        "headline": cae.headline,
                        "severity": dec.level,
                        "reason": dec.reason,
                        "home_coordinates": self.home_coordinates,
                        "policy_mode": self.policy_mode
                    })
                    
                    # 트리거된 경보 메트릭 증가
                    metrics.alerts_triggered.labels(
                        severity=cae.severity,
                        level=dec.level
                    ).inc()
                    
                    # 음성 알림 (비동기로 실행)
                    if self.voice_enabled:
                        asyncio.create_task(self._send_voice_alert(cae, dec))
                    
                    log.info("경보 발송됨", 
                            event_id=cae.event_id,
                            severity=cae.severity,
                            level=dec.level,
                            reason=dec.reason,
                            home_coordinates=self.home_coordinates,
                            voice_enabled=self.voice_enabled)
                
                # 전체 처리 시간 측정
                total_time = time.perf_counter() - t0
                metrics.end_to_end_seconds.observe(total_time)
                
            except Exception as e:
                log.error("메시지 처리 오류", 
                          error=str(e),
                          event_id=raw.get("id", "unknown"))
                continue
    
    async def _send_voice_alert(self, cae: CAE, decision: Decision) -> None:
        """
        음성 알림을 발송합니다.
        
        Args:
            cae: CAE 모델
            decision: 정책 평가 결과
        """
        try:
            # 위치 정보 추출
            location = None
            if cae.areas and len(cae.areas) > 0:
                location = cae.areas[0].name
            
            # 음성 메시지 생성
            voice_info = create_voice_message(
                cae, decision,
                language=self.voice_language,
                location=location,
                include_time=True
            )
            
            # TTS 엔진으로 음성 재생
            success = await self.tts_engine.speak(
                message=voice_info["message"],
                voice=voice_info["voice"],
                volume=voice_info["volume"],
                priority=voice_info["priority"]
            )
            
            if success:
                log.info("음성 알림 발송됨", 
                        event_id=cae.event_id,
                        message=voice_info["message"][:50] + "..." if len(voice_info["message"]) > 50 else voice_info["message"],
                        voice=voice_info["voice"],
                        volume=voice_info["volume"])
            else:
                log.error("음성 알림 발송 실패", event_id=cae.event_id)
                
        except Exception as e:
            log.error("음성 알림 처리 오류", 
                      error=str(e),
                      event_id=cae.event_id)
    
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
                
                # TTS 큐 크기 메트릭 업데이트
                if self.voice_enabled:
                    tts_queue_size = await self.tts_engine.get_queue_size()
                    # TTS 큐 크기 메트릭이 있다면 업데이트
                    # metrics.tts_queue_size.set(tts_queue_size)
                
                await asyncio.sleep(30)  # 30초마다 업데이트
                
            except Exception as e:
                log.error("메트릭 업데이트 오류", error=str(e))
                await asyncio.sleep(30)
