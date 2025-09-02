import asyncio
import json
import ssl
from typing import AsyncIterator, Dict
# 패키지에 따라 둘 중 하나 사용하세요. 현재는 aiomqtt를 쓰셨으니 그대로 갑니다.
from aiomqtt import Client, MqttError, Will
# from asyncio_mqtt import Client, MqttError, Will

from app.observability.logging_setup import get_logger
log = get_logger("dxsafety.mqtt_remote")

class RemoteMqttIngestor:
    """원격 MQTT 수집 어댑터"""

    def __init__(
        self,
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
        lwt_retain: bool = True,
    ):
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
        self._running = True
        while self._running:
            try:
                await self._connect()
                await self._subscribe()

                assert self.client is not None
                async with self.client.messages() as messages:
                    async for message in messages:
                        if not self._running:
                            break
                        try:
                            payload = json.loads(message.payload.decode("utf-8"))
                            yield payload
                        except json.JSONDecodeError as e:
                            log.error(f"JSON 파싱 오류: {e}")
                        except UnicodeDecodeError as e:
                            log.error(f"문자열 디코딩 오류: {e}")
                        except Exception as e:
                            log.error(f"메시지 처리 오류: {e}")

            except MqttError as e:
                log.error(f"MQTT 오류: {e}")
                if self._running:
                    await asyncio.sleep(5)  # 재연결 대기
            except Exception as e:
                log.error(f"예상치 못한 오류: {e}")
                if self._running:
                    await asyncio.sleep(5)
            finally:
                if self.client:
                    try:
                        await self.client.disconnect()
                    except Exception:
                        pass
                    self.client = None

    async def _connect(self) -> None:
        """MQTT 브로커에 연결합니다."""
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None

        # TLS 컨텍스트 준비 (필요 시)
        tls_context = None
        if self.tls:
            tls_context = ssl.create_default_context()
            # 필요 시 인증서 검증 커스터마이즈:
            # tls_context.check_hostname = False
            # tls_context.verify_mode = ssl.CERT_NONE

        # LWT 는 dict가 아니라 Will 객체로!
        will = Will(
            topic=self.lwt_topic,
            payload=self.lwt_payload.encode("utf-8"),
            qos=self.lwt_qos,
            retain=self.lwt_retain,
        )

        self.client = Client(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            client_id=self.client_id,
            keepalive=self.keepalive,
            clean_session=self.clean_session,
            tls_context=tls_context,  # aiomqtt/asyncio-mqtt는 tls_context 사용
            will=will,
        )

        await self.client.connect()
        log.info(f"MQTT 브로커 연결됨: {self.host}:{self.port}")

    async def _subscribe(self) -> None:
        if not self.client:
            raise RuntimeError("MQTT 클라이언트가 연결되지 않았습니다")
        await self.client.subscribe(self.topic)
        log.info(f"토픽 구독됨: {self.topic}")

    async def stop(self) -> None:
        self._running = False
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            log.info("MQTT 연결 종료됨")
