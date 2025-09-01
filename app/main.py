# app/main.py
import os, asyncio, signal
from typing import Optional
from app.settings import Settings
from app.observability.health import create_app
from app.adapters.mqtt_remote.client_async import RemoteMqttIngestor
from app.adapters.mqtt_local.publisher_async import LocalMqttPublisher
from app.adapters.storage.sqlite_outbox import SQLiteOutbox
from app.adapters.storage.sqlite_idem import SQLiteIdemStore
from app.adapters.homeassistant.client import HAClient
from app.orchestrators.orchestrator import Orchestrator  # 리네임된 P5

def _b(name, default=False): return os.getenv(name, str(default)).lower() in ("1","true","yes","on")

def build_settings() -> Settings:
    s = Settings()
    s.dry_run = _b("DRY_RUN", getattr(s, "dry_run", False))
    setattr(s, "rollback_mode", _b("ROLLBACK_MODE", False))
    s.remote_mqtt.host = os.getenv("REMOTE_MQTT_HOST", s.remote_mqtt.host)
    s.remote_mqtt.port = int(os.getenv("REMOTE_MQTT_PORT", s.remote_mqtt.port))
    s.local_mqtt.host  = os.getenv("LOCAL_MQTT_HOST", s.local_mqtt.host)
    s.local_mqtt.port  = int(os.getenv("LOCAL_MQTT_PORT", s.local_mqtt.port))
    s.geopolicy.mode = os.getenv("GEO_MODE", s.geopolicy.mode)
    s.geopolicy.severity_threshold = os.getenv("SEVERITY_THRESHOLD", s.geopolicy.severity_threshold)
    s.geopolicy.distance_km_threshold = float(os.getenv("DISTANCE_KM_THRESHOLD", s.geopolicy.distance_km_threshold))
    s.ha.base_url = os.getenv("HA_BASE_URL", s.ha.base_url)
    s.ha.token = os.getenv("HA_TOKEN", s.ha.token)
    s.observability.metrics_enabled = _b("METRICS_ENABLED", s.observability.metrics_enabled)
    s.observability.http_port = int(os.getenv("METRICS_PORT", s.observability.http_port))
    return s

async def start_http(settings: Settings) -> Optional[asyncio.Task]:
    if not settings.observability.metrics_enabled: return None
    import uvicorn
    app = create_app(settings)
    return asyncio.create_task(uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=settings.observability.http_port, log_level="info")
    ).serve())

async def main():
    s = build_settings()

    ingest = RemoteMqttIngestor(
        host=s.remote_mqtt.host, port=s.remote_mqtt.port, topic=s.remote_topic,
        username=s.remote_mqtt.username, password=s.remote_mqtt.password,
        tls=s.remote_mqtt.tls, client_id=s.remote_mqtt.client_id,
        keepalive=s.remote_mqtt.keepalive, clean_session=s.remote_mqtt.clean_session,
        lwt_topic=s.remote_mqtt.lwt_topic, lwt_payload=s.remote_mqtt.lwt_payload,
        lwt_qos=s.remote_mqtt.lwt_qos, lwt_retain=s.remote_mqtt.lwt_retain,
    )
    outbox = SQLiteOutbox(s.reliability.outbox_path); await outbox.init()
    publisher = LocalMqttPublisher(
        broker_host=s.local_mqtt.host, broker_port=s.local_mqtt.port, topic_prefix=s.local_mqtt.local_topic_prefix if hasattr(s.local_mqtt,'local_topic_prefix') else s.local_mqtt.host,
        outbox=outbox, username=s.local_mqtt.username, password=s.local_mqtt.password,
        tls=s.local_mqtt.tls, client_id=s.local_mqtt.client_id, keepalive=s.local_mqtt.keepalive,
        lwt_topic=s.local_mqtt.lwt_topic, lwt_payload_online="online",
        qos_default=1, retain_default=False,
        backoff_initial=s.reliability.backoff_initial_sec, backoff_max=s.reliability.backoff_max_sec,
        max_retries=s.reliability.publish_max_retries,
    )
    idem = SQLiteIdemStore(s.reliability.idem_path, s.reliability.idempotency_ttl_sec); await idem.init()
    ha = HAClient(s)

    # HA 좌표 실패 시 자동 폴백(운영 친화)
    try:
        await ha.get_home_location_cached(ttl_sec=300)
    except Exception:
        s.geopolicy.mode = "OR"  # severity-only로도 동작하도록 완화

    orch = Orchestrator(ingest, publisher, idem, ha, s)
    http_task = await start_http(s)

    stop = asyncio.Future()
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try: loop.add_signal_handler(sig, lambda: (not stop.done()) and stop.set_result(True))
            except NotImplementedError: pass
    except RuntimeError: pass

    orch_task = asyncio.create_task(orch.start())
    await stop
    orch_task.cancel()
    if http_task: http_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
