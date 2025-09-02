"""
Local MQTT publisher adapter for DX-Safety.

This module implements the local MQTT publisher adapter
with outbox pattern for durable message delivery.
"""

import asyncio
import json
from typing import Optional
from aiomqtt import Client, MqttError
from app.adapters.storage.sqlite_outbox import SQLiteOutbox
from app.common.retry import exponential_backoff
from app.observability.logging_setup import get_logger

log = get_logger("dxsafety.mqtt_local")

class LocalMqttPublisher:
    """로컬 MQTT 발송 어댑터 (Outbox 패턴)"""
    
    def __init__(self, 
                 *,
                 broker_host: str,
                 broker_port: int,
                 topic_prefix: str,
                 outbox: SQLiteOutbox,
                 username: str | None = None,
                 password: str | None = None,
                 tls: bool = False,
                 client_id: str | None = None,
                 keepalive: int = 30,
                 lwt_topic: str = "dxsafety/state",
                 lwt_payload_online: str = "online",
                 qos_default: int = 1,
                 retain_default: bool = False,
                 backoff_initial: float = 0.5,
                 backoff_max: float = 30.0,
                 max_retries: int = 10):
        """
        초기화합니다.
        
        Args:
            broker_host: MQTT 브로커 호스트
            broker_port: MQTT 브로커 포트
            topic_prefix: 토픽 접두사
            outbox: Outbox 인스턴스
            username: 사용자명
            password: 비밀번호
            tls: TLS 사용 여부
            client_id: 클라이언트 ID
            keepalive: keepalive 시간
            lwt_topic: Last Will and Testament 토픽
            lwt_payload_online: 온라인 상태 페이로드
            qos_default: 기본 QoS
            retain_default: 기본 retain 플래그
            backoff_initial: 초기 백오프 시간
            backoff_max: 최대 백오프 시간
            max_retries: 최대 재시도 횟수
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_prefix = topic_prefix.rstrip("/")
        self.outbox = outbox
        self.username = username
        self.password = password
        self.tls = tls
        self.client_id = client_id
        self.keepalive = keepalive
        self.lwt_topic = lwt_topic
        self.lwt_payload_online = lwt_payload_online
        self.qos_default = qos_default
        self.retain_default = retain_default
        self.backoff_initial = backoff_initial
        self.backoff_max = backoff_max
        self.max_retries = max_retries
        
        self.client: Client | None = None
        self._running = False
    
    async def start(self) -> None:
        """발송 워커를 시작합니다."""
        self._running = True
        
        # MQTT 연결
        await self._connect()
        
        # Outbox 워커 시작
        while self._running:
            try:
                await self._process_outbox()
                await asyncio.sleep(1)  # 1초 대기
            except Exception as e:
                log.error(f"Outbox 처리 오류: {e}")
                await asyncio.sleep(5)  # 오류 시 5초 대기
    
    async def _connect(self) -> None:
        """MQTT 브로커에 연결합니다."""
        connect_kwargs = {
            "hostname": self.broker_host,
            "port": self.broker_port,
            "keepalive": self.keepalive
        }
        
        if self.username:
            connect_kwargs["username"] = self.username
        if self.password:
            connect_kwargs["password"] = self.password
        if self.client_id:
            connect_kwargs["client_id"] = self.client_id
        
        if self.tls:
            connect_kwargs["tls"] = True
        
        # LWT 설정
        connect_kwargs["will"] = {
            "topic": self.lwt_topic,
            "payload": "offline",
            "qos": 1,
            "retain": True
        }
        
        self.client = Client(**connect_kwargs)
        await self.client.connect()
        
        # 온라인 상태 발송
        await self.client.publish(
            self.lwt_topic,
            self.lwt_payload_online,
            qos=1,
            retain=True
        )
        
        log.info(f"로컬 MQTT 브로커 연결됨: {self.broker_host}:{self.broker_port}")
    
    async def _process_outbox(self) -> None:
        """Outbox의 메시지를 처리합니다."""
        item = await self.outbox.peek_oldest()
        if not item:
            return
        
        # 최대 재시도 횟수 확인
        if item.attempts >= self.max_retries:
            log.warning(f"최대 재시도 횟수 초과, 항목 삭제: {item.id}")
            await self.outbox.delete(item.id)
            return
        
        try:
            # MQTT 발송
            await self.client.publish(
                item.topic,
                item.payload,
                qos=item.qos,
                retain=item.retain
            )
            
            # 성공 시 항목 삭제
            await self.outbox.delete(item.id)
            log.info(f"메시지 발송 성공: id:{item.id} topic:{item.topic} payload:{item.payload}")
            
        except Exception as e:
            log.error(f"메시지 발송 실패: id:{item.id} topic:{item.topic} error:{str(e)}")
            
            # 재시도 횟수 증가
            await self.outbox.mark_attempt(item.id)
            
            # 백오프 대기
            await exponential_backoff(
                item.attempts + 1,
                self.backoff_initial,
                self.backoff_max
            )
    
    async def enqueue_json(self, topic_suffix: str, payload_obj: dict, 
                          qos: Optional[int] = None, retain: Optional[bool] = None) -> int:
        """
        JSON 객체를 Outbox에 추가합니다.
        
        Args:
            topic_suffix: 토픽 접미사
            payload_obj: 발송할 JSON 객체
            qos: QoS 레벨 (None이면 기본값 사용)
            retain: retain 플래그 (None이면 기본값 사용)
            
        Returns:
            생성된 Outbox 항목의 ID
        """
        topic = f"{self.topic_prefix}/{topic_suffix}"
        payload = json.dumps(payload_obj, ensure_ascii=False).encode('utf-8')
        
        return await self.outbox.enqueue(
            topic,
            payload,
            qos or self.qos_default,
            retain if retain is not None else self.retain_default
        )
    
    async def stop(self) -> None:
        """발송을 중지합니다."""
        self._running = False
        if self.client:
            await self.client.disconnect()
            log.info("로컬 MQTT 연결 종료됨")
