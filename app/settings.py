# app/settings.py
from __future__ import annotations
from pydantic import BaseModel, Field

class MqttCommon(BaseModel):
    host: str = "core-mosquitto"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    tls: bool = False
    client_id: str | None = None
    keepalive: int = 30
    clean_session: bool = False
    lwt_topic: str = "dxsafety/state"
    lwt_payload: str = "offline"
    lwt_qos: int = 1
    lwt_retain: bool = True

class RemoteMQTT(MqttCommon):
    topic: str = "pws/cap/#"
    qos: int = 1

class LocalMQTT(MqttCommon):
    topic_prefix: str = "dxsafety"
    qos: int = 1
    retain: bool = False

class HAConfig(BaseModel):
    base_url: str = "http://supervisor/core/api"
    token: str = ""
    timeout_sec: int = 5

class GeoPolicy(BaseModel):
    mode: str = "AND"                         # AND | OR
    severity_threshold: str = "moderate"      # minor|moderate|severe|critical
    distance_km_threshold: float = 5.0
    polygon_buffer_km: float = 0.0

class Observability(BaseModel):
    http_port: int = 8099
    metrics_enabled: bool = True
    service_name: str = "DX-Safety"
    build_version: str = "0.1.3"
    build_date: str = "2025-01-01"
    log_level: str = "INFO"

class Reliability(BaseModel):
    idempotency_ttl_sec: int = 86400
    outbox_path: str = "/data/outbox.db"
    idem_path: str = "/data/idem.db"
    publish_max_retries: int = 10
    backoff_initial_sec: float = 0.5
    backoff_max_sec: float = 30.0
    queue_maxsize: int = 1000
    drop_on_full: bool = False

class Settings(BaseModel):
    # 상위 플래그(옵션)
    dry_run: bool = False
    rollback_mode: bool = False
    
    # 하위 섹션 (기본값/팩토리로 누락 방지)
    remote_mqtt: RemoteMQTT = Field(default_factory=RemoteMQTT)
    local_mqtt: LocalMQTT = Field(default_factory=LocalMQTT)
    ha: HAConfig = Field(default_factory=HAConfig)
    geopolicy: GeoPolicy = Field(default_factory=GeoPolicy)
    observability: Observability = Field(default_factory=Observability)
    reliability: Reliability = Field(default_factory=Reliability)
    tts: 'TTS' = Field(default_factory=lambda: TTS())

class TTS(BaseModel):
    enabled: bool = False
    topic: str = "dxsafety/tts"
    template: str = "{headline} - {description}"
    voice_language: str = "ko-KR"