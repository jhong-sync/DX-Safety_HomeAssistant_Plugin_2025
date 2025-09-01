from pydantic import BaseModel
from typing import Optional
import os
import json
from app.observability.logger import get_logger

log = get_logger()


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
    enabled: bool = True  # MQTT 기능을 선택적으로 활성화


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
    # 재시도 설정
    max_retries: int = 5
    initial_delay: float = 1.0
    max_delay: float = 120.0
    backoff_factor: float = 2.0
    jitter: bool = True


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
        
        # Home Assistant 환경에서 Supervisor 토큰 자동 감지
        if not data.get("homeassistant_api", {}).get("token"):
            supervisor_token = os.getenv("SUPERVISOR_TOKEN")
            if supervisor_token:
                if "homeassistant_api" not in data:
                    data["homeassistant_api"] = {}
                data["homeassistant_api"]["token"] = supervisor_token
                log.info("Supervisor 토큰이 자동으로 설정되었습니다")
            else:
                log.warning("SUPERVISOR_TOKEN 환경변수가 없습니다. Home Assistant API 기능이 제한될 수 있습니다.")
        
        return Settings(**data)

