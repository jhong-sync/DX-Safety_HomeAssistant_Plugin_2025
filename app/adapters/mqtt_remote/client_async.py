"""
Remote MQTT ingestion adapter for DX-Safety.

This module implements the remote MQTT ingestion adapter
with reliability features including reconnect logic and LWT.
"""

import asyncio
import json
from typing import AsyncIterator, Dict
from aiomqtt import Client, MqttError
from app.observability.logger import get_logger

log = get_logger()

class RemoteMqttIngestor:
    """원격 MQTT 수집 어댑터"""
    
    def __init__(self, 
                 host: str, 
                 port: int, 
                 topic: str,
                 *,
                 username: str | None = None,
                 password: str | None = None,
                 tls: bool = False,
                 client_id: str | None = None,
                 keepalive: int = 30,
                 clean_session: bool = False,
                 lwt_topic: str = "dxsafety/state",
                 lwt_payload: str = "offline",
                 lwt_qos: int = 1,
                 lwt_retain: bool = True):
        """
        초기화합니다.
        
        Args:
            host: MQTT 브로커 호스트
            port: MQTT 브로커 포트
            topic: 구독할 토픽
            username: 사용자명
            password: 비밀번호
            tls: TLS 사용 여부
            client_id: 클라이언트 ID
            keepalive: keepalive 시간
            clean_session: clean session 여부
            lwt_topic: Last Will and Testament 토픽
            lwt_payload: LWT 페이로드
            lwt_qos: LWT QoS
            lwt_retain: LWT retain 플래그
        """
        self.host = host
        self.port = port
        self.topic = topic
        self.username = username
        self.password = password
        self.tls = tls
        self.client_id = client_id
        self.keepalive = keepalive
        self.clean_session = clean_session
        self.lwt_topic = lwt_topic
        self.lwt_payload = lwt_payload
        self.lwt_qos = lwt_qos
        self.lwt_retain = lwt_retain
        
        self.client: Client | None = None
        self._running = False
    
    async def recv(self) -> AsyncIterator[Dict]:
        """
        원시 경보 데이터를 비동기적으로 수신합니다.
        
        Yields:
            원시 딕셔너리 데이터
        """
        self._running = True
        
        while self._running:
            try:
                await self._connect()
                await self._subscribe()
                
                async with self.client.messages() as messages:
                    async for message in messages:
                        if not self._running:
                            break
                        
                        try:
                            # JSON 파싱
                            payload = json.loads(message.payload.decode('utf-8'))
                            yield payload
                        except json.JSONDecodeError as e:
                            log.error(f"JSON 파싱 오류: {e}")
                        except Exception as e:
                            log.error(f"메시지 처리 오류: {e}")
                            
            except MqttError as e:
                log.error(f"MQTT 오류: {e}")
                if self._running:
                    await asyncio.sleep(5)  # 재연결 전 대기
            except Exception as e:
                log.error(f"예상치 못한 오류: {e}")
                if self._running:
                    await asyncio.sleep(5)
    
    async def _connect(self) -> None:
        """MQTT 브로커에 연결합니다."""
        if self.client:
            await self.client.disconnect()
        
        # 연결 옵션 구성
        connect_kwargs = {
            "hostname": self.host,
            "port": self.port,
            "keepalive": self.keepalive,
            "clean_session": self.clean_session
        }
        
        if self.username:
            connect_kwargs["username"] = self.username
        if self.password:
            connect_kwargs["password"] = self.password
        if self.client_id:
            connect_kwargs["client_id"] = self.client_id
        
        # TLS 설정
        if self.tls:
            connect_kwargs["tls"] = True
        
        # LWT 설정
        connect_kwargs["will"] = {
            "topic": self.lwt_topic,
            "payload": self.lwt_payload,
            "qos": self.lwt_qos,
            "retain": self.lwt_retain
        }
        
        self.client = Client(**connect_kwargs)
        await self.client.connect()
        log.info(f"MQTT 브로커 연결됨: {self.host}:{self.port}")
    
    async def _subscribe(self) -> None:
        """토픽을 구독합니다."""
        if not self.client:
            raise RuntimeError("MQTT 클라이언트가 연결되지 않았습니다")
        
        await self.client.subscribe(self.topic)
        log.info(f"토픽 구독됨: {self.topic}")
    
    async def stop(self) -> None:
        """수집을 중지합니다."""
        self._running = False
        if self.client:
            await self.client.disconnect()
            log.info("MQTT 연결 종료됨")
