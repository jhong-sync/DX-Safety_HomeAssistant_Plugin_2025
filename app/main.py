# app/main.py
import os, asyncio, signal
from typing import Optional
import uvicorn
from app.adapters.tts.engine import TTSEngine
from app.settings import Settings
from app.observability.health import create_app
from app.observability.logger import setup_logger, get_logger
from app.adapters.mqtt_remote.client_async import RemoteMqttIngestor
from app.adapters.mqtt_local.publisher_async import LocalMqttPublisher
from app.adapters.storage.sqlite_outbox import SQLiteOutbox
from app.adapters.storage.sqlite_idem import SQLiteIdemStore
from app.adapters.homeassistant.client import HAClient
from app.orchestrators.orchestrator import Orchestrator

def _b(name, default=False): return os.getenv(name, str(default)).lower() in ("1","true","yes","on")

def build_settings() -> Settings:
    s = Settings()
    # 플래그
    s.dry_run = _b("DRY_RUN", getattr(s, "dry_run", False))
    setattr(s, "rollback_mode", _b("ROLLBACK_MODE", False))

    # REMOTE MQTT
    s.remote_mqtt.host = os.getenv("REMOTE_MQTT_HOST", s.remote_mqtt.host)
    s.remote_mqtt.port = int(os.getenv("REMOTE_MQTT_PORT", s.remote_mqtt.port))
    s.remote_mqtt.username = os.getenv("REMOTE_MQTT_USERNAME", s.remote_mqtt.username)
    s.remote_mqtt.password = os.getenv("REMOTE_MQTT_PASSWORD", s.remote_mqtt.password)
    s.remote_mqtt.client_id = os.getenv("REMOTE_MQTT_CLIENT_ID", s.remote_mqtt.client_id)
    s.remote_mqtt.keepalive = int(os.getenv("REMOTE_MQTT_KEEPALIVE", s.remote_mqtt.keepalive))
    s.remote_mqtt.clean_session = _b("REMOTE_MQTT_CLEAN_SESSION", s.remote_mqtt.clean_session)
    s.remote_mqtt.tls = _b("REMOTE_MQTT_TLS", s.remote_mqtt.tls)
    s.remote_mqtt.topic = os.getenv("REMOTE_TOPIC", s.remote_mqtt.topic)

    # LOCAL MQTT
    s.local_mqtt.host  = os.getenv("LOCAL_MQTT_HOST", s.local_mqtt.host)
    s.local_mqtt.port  = int(os.getenv("LOCAL_MQTT_PORT", s.local_mqtt.port))
    s.local_mqtt.username = os.getenv("LOCAL_MQTT_USERNAME", s.local_mqtt.username)
    s.local_mqtt.password = os.getenv("LOCAL_MQTT_PASSWORD", s.local_mqtt.password)
    s.local_mqtt.topic_prefix = os.getenv("LOCAL_TOPIC_PREFIX", s.local_mqtt.topic_prefix)

    # 정책
    s.geopolicy.mode = os.getenv("GEO_MODE", s.geopolicy.mode)
    s.geopolicy.severity_threshold = os.getenv("SEVERITY_THRESHOLD", s.geopolicy.severity_threshold)
    s.geopolicy.distance_km_threshold = float(os.getenv("DISTANCE_KM_THRESHOLD", s.geopolicy.distance_km_threshold))
    s.geopolicy.polygon_buffer_km = float(os.getenv("POLYGON_BUFFER_KM", s.geopolicy.polygon_buffer_km))
    s.tts.enabled = _b("TTS_ENABLED", s.tts.enabled)
    s.tts.voice_language = os.getenv("TTS_VOICE_LANGUAGE", s.tts.voice_language)

    # HA
    s.ha.base_url = os.getenv("HA_BASE_URL", s.ha.base_url)
    s.ha.token = os.getenv("HA_TOKEN", s.ha.token)

    # 관측성
    s.observability.metrics_enabled = _b("METRICS_ENABLED", s.observability.metrics_enabled)
    s.observability.http_port = int(os.getenv("METRICS_PORT", s.observability.http_port))

    # 신뢰성
    s.reliability.queue_maxsize = int(os.getenv("QUEUE_MAXSIZE", s.reliability.queue_maxsize))

    # TTS
    s.tts.topic = os.getenv("TTS_TOPIC", s.tts.topic)
    s.tts.template = os.getenv("TTS_TEMPLATE", s.tts.template)
    s.tts.voice_language = os.getenv("TTS_VOICE_LANGUAGE", s.tts.voice_language)

    return s

async def start_http(settings: Settings) -> Optional[asyncio.Task]:
    if not settings.observability.metrics_enabled: return None
    app = create_app(settings)
    return asyncio.create_task(uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=settings.observability.http_port, log_level="info")
    ).serve())

async def main():
    # 로거 초기화 (환경변수 LOG_LEVEL 우선, 없으면 설정 사용)
    initial_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logger(level=initial_level)
    log = get_logger()
    
    s = build_settings()
    # 설정된 로그 레벨로 재설정
    log.info("설정 로드 완료")
    ingest = RemoteMqttIngestor(
        host=s.remote_mqtt.host,
        port=s.remote_mqtt.port,
        topic=s.remote_mqtt.topic,
        username=s.remote_mqtt.username,
        password=s.remote_mqtt.password,
        tls=s.remote_mqtt.tls,
        client_id=s.remote_mqtt.client_id,
        keepalive=s.remote_mqtt.keepalive,
        clean_session=s.remote_mqtt.clean_session,
        lwt_topic=s.remote_mqtt.lwt_topic,
        lwt_payload=s.remote_mqtt.lwt_payload,
        lwt_qos=s.remote_mqtt.lwt_qos,
        lwt_retain=s.remote_mqtt.lwt_retain,
    )
    log.info("원격 MQTT 인게스터 생성 완료")
    
    outbox = SQLiteOutbox(s.reliability.outbox_path); await outbox.init()
    
    publisher = LocalMqttPublisher(
        broker_host=s.local_mqtt.host,
        broker_port=s.local_mqtt.port,
        topic_prefix=s.local_mqtt.topic_prefix,
        outbox=outbox,
        username=s.local_mqtt.username,
        password=s.local_mqtt.password,
        tls=s.local_mqtt.tls,
        client_id=s.local_mqtt.client_id,
        keepalive=s.local_mqtt.keepalive,
        lwt_topic=s.local_mqtt.lwt_topic,
        lwt_payload_online="online",
        qos_default=1,
        retain_default=False,
        backoff_initial=s.reliability.backoff_initial_sec,
        backoff_max=s.reliability.backoff_max_sec,
        max_retries=s.reliability.publish_max_retries,
    )
    log.info("로컬 MQTT 퍼블리셔 생성 완료")
    
    idem = SQLiteIdemStore(s.reliability.idem_path, s.reliability.idempotency_ttl_sec); await idem.init()
    
    ha = HAClient(
        base_url=s.ha.base_url,
        token=s.ha.token,
        timeout=10
    )
    
    tts_engine = TTSEngine(
        ha_client=ha,
        default_voice=s.tts.voice_language
        )
    
    # HA 좌표 실패 시 자동 폴백(운영 친화)
    try:
        async with ha:
            coords = await ha.get_zone_home()
            if not coords:
                s.geopolicy.mode = "OR"  # severity-only로도 동작하도록 완화
                log.warning("HA 홈 좌표를 가져올 수 없음, 정책 모드 OR로 폴백")
            else:
                log.info("HA 홈 좌표 조회 성공")
    except Exception as e:
        s.geopolicy.mode = "OR"  # severity-only로도 동작하도록 완화
        log.warning("HA 좌표 조회 실패, 정책 모드 OR로 폴백")

    orch = Orchestrator(ingest, publisher, idem, ha, tts_engine, severity_threshold=s.geopolicy.severity_threshold, distance_threshold_km=s.geopolicy.distance_km_threshold, polygon_buffer_km=s.geopolicy.polygon_buffer_km, policy_mode=s.geopolicy.mode, voice_enabled=s.tts.enabled, voice_language=s.tts.voice_language, queue_maxsize=s.reliability.queue_maxsize)
    log.info("오케스트레이터 생성 완료")
    
    http_task = await start_http(s)
    if http_task:
        log.info("HTTP 서버 시작됨")

    stop = asyncio.Future()
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try: loop.add_signal_handler(sig, lambda: (not stop.done()) and stop.set_result(True))
            except NotImplementedError: pass
    except RuntimeError: pass

    log.info("오케스트레이터 시작")
    orch_task = asyncio.create_task(orch.start())
    await stop
    orch_task.cancel()
    if http_task: http_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
