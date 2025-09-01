import asyncio
import ssl
import socket, uuid, os, logging, traceback
import paho.mqtt.client as mqtt
from app.observability.logger import get_logger
from app.utils.retry import RetryManager

def _make_client_id(prefix="dxsafety") -> str:
    base = f"{prefix}-{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
    return base[:23]

log = get_logger()
paho_log = logging.getLogger("paho")
paho_log.setLevel(logging.DEBUG if os.getenv("LOG_LEVEL","INFO").upper()=="DEBUG" else logging.WARNING)

class MqttIngestor:
    def __init__(self, cfg, on_message, metrics, loop: asyncio.AbstractEventLoop | None = None):
        self.cfg = cfg
        self.on_message_cb = on_message
        self.metrics = metrics
        self.loop = loop or asyncio.get_event_loop()
        
        # 설정에서 재시도 옵션 가져오기
        reliability_cfg = getattr(cfg, 'reliability', None)
        if reliability_cfg:
            self.retry_manager = RetryManager(
                max_retries=getattr(reliability_cfg, 'max_retries', 10),
                initial_delay=getattr(reliability_cfg, 'initial_delay', 1.0),
                max_delay=getattr(reliability_cfg, 'max_delay', 120.0),
                backoff_factor=getattr(reliability_cfg, 'backoff_factor', 2.0),
                jitter=getattr(reliability_cfg, 'jitter', True)
            )
        else:
            self.retry_manager = RetryManager(
                max_retries=10,
                initial_delay=1.0,
                max_delay=120.0,
                backoff_factor=2.0,
                jitter=True
            )

        # --- 설정 요약 로그 (민감정보 제외) ---
        mode = getattr(cfg, "security_mode", "none")
        log.info({
            "msg": "[Remote MQTT] mqtt_config",
            "host": getattr(cfg,"host",""),
            "port": getattr(cfg,"port",0),
            "mode": mode,
            "username_present": bool(getattr(cfg,"username","")),
            "clean_session": getattr(cfg,"clean_session", True)
        })

        # --- client_id 생성 ---
        client_id = (getattr(cfg, "client_id", "") or "").strip()
        if (not cfg.clean_session) and not client_id:
            client_id = _make_client_id()

        try:
            self.client = mqtt.Client(
                client_id=client_id or None,
                clean_session=cfg.clean_session
            )
        except Exception as e:
            log.exception({"msg": "mqtt_client_init_error", "error": str(e)})
            raise

        # --- TLS 분기: security_mode 기준 ---
        if mode in ("tls", "mtls"):
            ca = getattr(cfg, "ca_cert_path", "") or ""
            crt = getattr(cfg, "client_cert_path", "") or ""
            key = getattr(cfg, "client_key_path", "") or ""
            if not ca or not os.path.exists(ca):
                log.error({"msg": "ca_missing_or_invalid", "path": ca})
            if mode == "mtls":
                if not crt or not os.path.exists(crt):
                    log.error({"msg": "client_cert_missing_or_invalid", "path": crt})
                if not key or not os.path.exists(key):
                    log.error({"msg": "client_key_missing_or_invalid", "path": key})

            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if ca:  ctx.load_verify_locations(cafile=ca)
            if mode == "mtls" and crt and key:
                ctx.load_cert_chain(certfile=crt, keyfile=key)
            self.client.tls_set_context(ctx)

        # --- 사용자 인증 ---
        if getattr(cfg, "username", ""):
            self.client.username_pw_set(cfg.username, getattr(cfg, "password", ""))

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.will_set("dxsafety/status", payload="offline", qos=1, retain=True)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info({"msg": "[Remote MQTT] ingestor_connected", "rc": rc, "topic": self.cfg.topic})
            client.subscribe(self.cfg.topic, qos=self.cfg.qos)
            client.publish("dxsafety/status", payload="online", qos=1, retain=True)
        else:
            log.error({"msg": "[Remote MQTT] ingestor_connect_failed", "rc": rc})

    def _on_disconnect(self, client, userdata, rc):
        log.info({"msg": "[Remote MQTT] ingestor_disconnected", "rc": rc})
        try:
            self.metrics.ingestor_reconnects_total.inc()
        except Exception:
            pass

    def _on_message(self, client, userdata, message):
        try:
            fut = asyncio.run_coroutine_threadsafe(
                self.on_message_cb(message.payload, message.topic),
                self.loop
            )
        except Exception as e:
            log.exception({"msg":"[Remote MQTT] ingestor_on_message_error", "error": str(e)})

    async def _connect_with_retry(self):
        """재시도 로직으로 MQTT 연결"""
        return await self.retry_manager.execute_with_retry(
            self._connect_once,
            "[Remote MQTT] 연결"
        )
    
    def _connect_once(self):
        """단일 MQTT 연결 시도"""
        # 포트/모드 불일치 경고
        mode = getattr(self.cfg, "security_mode", "none")
        if (mode == "none" and self.cfg.port == 8883) or (mode in ("tls","mtls") and self.cfg.port == 1883):
            log.warning({"msg":"[Remote MQTT] mqtt_port_mode_mismatch","mode":mode,"port":self.cfg.port})

        # TCP 프리플라이트 (빠르게 원인 파악)
        try:
            sock = socket.create_connection((self.cfg.host, self.cfg.port), timeout=5)
            sock.close()
        except Exception as e:
            log.error({"msg":"[Remote MQTT] mqtt_tcp_unreachable","host":self.cfg.host,"port":self.cfg.port,"error":str(e)})
            raise

        # 접속
        self.client.connect(self.cfg.host, self.cfg.port, keepalive=self.cfg.keepalive)
        self.client.loop_start()
        return True

    async def run(self):
        while True:
            try:
                await self._connect_with_retry()
                
                # 메인 루프
                while True:
                    await asyncio.sleep(1)

            except Exception as e:
                log.exception({
                    "msg":"[Remote MQTT] ingestor_error",
                    "host": getattr(self.cfg,"host",""),
                    "port": getattr(self.cfg,"port",0),
                    "mode": getattr(self.cfg,"security_mode",""),
                    "topic": getattr(self.cfg,"topic",""),
                    "error": str(e)
                })
                
                # 재시도
                try:
                    self.client.loop_stop()
                except Exception:
                    pass
                
                # 재시도 매니저가 지연을 처리하므로 여기서는 대기하지 않음
                continue
