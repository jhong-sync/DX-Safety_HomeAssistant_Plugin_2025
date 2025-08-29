from pydantic import BaseModel
from typing import Optional
import os
import json


class RemoteMqtt(BaseModel):
    host: str
    port: int
    topic: str
    qos: int = 1
    # Security: none | tls | mtls
    security_mode: str = "none"
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    keepalive: int = 30
    clean_session: bool = False
    client_id: Optional[str] = None


class LocalMqtt(BaseModel):
    host: str
    port: int
    topic_prefix: str
    qos: int = 1
    retain: bool = True


class HomeAssistantAPI(BaseModel):
    token: Optional[str] = None
    url: str = "http://supervisor/core"
    timeout: int = 30


class Policy(BaseModel):
    default_location: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km_buffer: float = 0
    severity_threshold: str = "moderate"
    night_mode: bool = False


class TTS(BaseModel):
    enabled: bool = False
    topic: str
    template: str


class Observability(BaseModel):
    http_port: int = 8099
    metrics_enabled: bool = True
    log_level: str = "INFO"


class Reliability(BaseModel):
    idempotency_ttl_sec: int = 86400
    reconnect_max_backoff_sec: int = 120


class Settings(BaseModel):
    remote_mqtt: RemoteMqtt
    local_mqtt: LocalMqtt
    homeassistant_api: HomeAssistantAPI
    policy: Policy
    tts: TTS
    observability: Observability
    reliability: Reliability

    @staticmethod
    def load():
        # Use HA_OPTIONS_PATH if present, else default
        path = os.getenv("HA_OPTIONS_PATH", "/data/options.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Settings(**data)

