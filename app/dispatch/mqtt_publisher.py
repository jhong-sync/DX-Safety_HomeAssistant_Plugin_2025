import json
import paho.mqtt.client as mqtt
from app.observability.logger import get_logger
from app.utils.retry import RetryManager
import asyncio

log = get_logger()

class MqttPublisher:
    def __init__(self, cfg, metrics):
        self.cfg = cfg
        self.metrics = metrics
        self.client = mqtt.Client()
        self._connected = False
        self._connection_task = None
        
        # MQTT 인증 설정
        if hasattr(cfg, 'username') and cfg.username:
            self.client.username_pw_set(cfg.username, cfg.password or "")
            log.info(f"[Local MQTT] 인증 설정: username={cfg.username}")
        
        # MQTT 콜백 설정
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        # 설정에서 재시도 옵션 가져오기
        reliability_cfg = getattr(cfg, 'reliability', None)
        if reliability_cfg:
            self.retry_manager = RetryManager(
                max_retries=getattr(reliability_cfg, 'max_retries', 5),
                initial_delay=getattr(reliability_cfg, 'initial_delay', 2.0),
                max_delay=getattr(reliability_cfg, 'max_delay', 60.0),
                backoff_factor=getattr(reliability_cfg, 'backoff_factor', 2.0),
                jitter=getattr(reliability_cfg, 'jitter', True)
            )
        else:
            self.retry_manager = RetryManager(
                max_retries=5,
                initial_delay=2.0,
                max_delay=60.0,
                backoff_factor=2.0,
                jitter=True
            )
        
        # 연결을 지연시켜 서비스 준비 시간을 줍니다
        self._connection_task = asyncio.create_task(self._connect_with_retry())
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 연결 콜백"""
        if rc == 0:
            self._connected = True
            log.info(f"[Local MQTT] 연결 성공: {self.cfg.host}:{self.cfg.port}")
        else:
            self._connected = False
            log.error(f"[Local MQTT] 연결 실패 (코드 {rc}): {self._get_rc_description(rc)}")
    
    def _get_rc_description(self, rc):
        """MQTT 연결 결과 코드 설명"""
        rc_descriptions = {
            0: "연결 성공",
            1: "잘못된 프로토콜 버전",
            2: "잘못된 클라이언트 식별자",
            3: "서버 사용 불가",
            4: "잘못된 사용자명 또는 비밀번호",
            5: "인증되지 않음"
        }
        return rc_descriptions.get(rc, f"알 수 없는 오류 코드 {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT 연결 해제 콜백"""
        self._connected = False
        log.info(f"[Local MQTT] 연결 해제: {rc}")
    
    async def _connect_with_retry(self):
        """MQTT 연결을 재시도하면서 연결합니다."""
        try:
            await self.retry_manager.execute_with_retry(
                self._connect_once,
                "[Local MQTT] 연결"
            )
            self._connected = True
            log.info("[Local MQTT] 연결 성공")
        except Exception as e:
            log.error(f"[Local MQTT] 연결 최종 실패 - 로컬 MQTT 기능 비활성화: {e}")
            self._connected = False
    
    def _connect_once(self):
        """단일 MQTT 연결 시도"""
        try:
            log.info(f"[Local MQTT] 연결 시도: {self.cfg.host}:{self.cfg.port}")
            
            # Node.js 스타일 연결 설정
            self.client.connect(
                host=self.cfg.host,
                port=self.cfg.port,
                keepalive=60,  # Node.js 기본값과 유사
                bind_address=""  # 기본 바인드 주소
            )
            self.client.loop_start()
            return True
        except Exception as e:
            log.warning(f"[Local MQTT] 연결 실패: {e}")
            raise
    
    async def _ensure_connected(self):
        """연결이 되어 있는지 확인하고 필요시 재연결"""
        if not self._connected:
            if self._connection_task and not self._connection_task.done():
                # 연결 작업이 진행 중이면 대기
                try:
                    await asyncio.wait_for(self._connection_task, timeout=10.0)
                except asyncio.TimeoutError:
                    log.warning("MQTT 연결 대기 시간 초과")
                    return False
            else:
                # 연결 작업이 완료되었지만 실패한 경우 재시도
                self._connection_task = asyncio.create_task(self._connect_with_retry())
                try:
                    await asyncio.wait_for(self._connection_task, timeout=30.0)
                except asyncio.TimeoutError:
                    log.warning("MQTT 재연결 대기 시간 초과")
                    return False
        return self._connected
    
    async def publish_alert(self, cae: dict, decision):
        if not await self._ensure_connected():
            log.warning("[Local MQTT] 연결되지 않음 - 알림 발행 건너뜀")
            return
            
        topic = f"{self.cfg.topic_prefix}/{decision.target_topic}"
        log.info({"msg": "[Local MQTT] publish_alert", "topic": topic, "cae": cae, "decision": decision})
        payload = json.dumps({"headline": cae["headline"], "severity": cae["severity"]}, ensure_ascii=False)
        
        try:
            result = self.client.publish(topic, payload=payload, qos=self.cfg.qos, retain=self.cfg.retain)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                log.error(f"[Local MQTT] 발행 실패: {result.rc}")
                # 발행 실패 시 재연결 시도
                if result.rc == mqtt.MQTT_ERR_NO_CONN:
                    log.info("[Local MQTT] 연결 끊어짐 감지 - 재연결 시도")
                    await self._connect_with_retry()
        except Exception as e:
            log.error(f"[Local MQTT] 발행 중 오류: {e}")

    async def publish_tts(self, topic: str, text: str, severity: str = ""):
        if not await self._ensure_connected():
            log.warning("[Local MQTT] 연결되지 않음 - TTS 발행 건너뜀")
            return
            
        # topic is expected to be absolute (e.g., "dxsafety/tts")
        payload = json.dumps({"text": text, "severity": severity}, ensure_ascii=False)
        
        try:
            result = self.client.publish(topic, payload=payload, qos=self.cfg.qos, retain=self.cfg.retain)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                log.error(f"[Local MQTT] TTS 발행 실패: {result.rc}")
        except Exception as e:
            log.error(f"[Local MQTT] TTS 발행 중 오류: {e}")
    
    async def close(self):
        """MQTT 연결을 정리합니다."""
        try:
            if self._connected:
                self.client.loop_stop()
                self.client.disconnect()
                log.info("[Local MQTT] 연결 정리 완료")
        except Exception as e:
            log.error(f"[Local MQTT] 연결 정리 중 오류: {e}")
