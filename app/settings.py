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
    username: Optional[str] = None
    password: Optional[str] = None


class HomeAssistantAPI(BaseModel):
    token: Optional[str] = None
    url: str = "http://supervisor/core"
    timeout: int = 30


class HAConfig(BaseModel):
    base_url: str = "http://supervisor/core/api"  # add-on 내부에서 supervisor 경유 가능
    token: str = ""  # Hass long-lived token or supervisor auto token
    timeout_sec: int = 3
    # 센서 업데이트 옵션
    publish_sensors: bool = False
    sensor_prefix: str = "sensor.dxsafety"


class GeoPolicy(BaseModel):
    mode: str = "AND"        # "AND" => severity & geo 모두 충족, "OR" => 둘 중 하나
    severity_threshold: str = "moderate"
    distance_km_threshold: float = 5.0  # home과 이벤트 영역의 최소 거리 기준
    polygon_buffer_km: float = 0.0      # (선택) 폴리곤 경계에 버퍼 적용
    use_shapely: bool = False


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
    service_name: str = "dxsafety-addon"
    build_version: str = "phase3"
    build_date: str = "2025-01-01"


class Reliability(BaseModel):
    # Idempotency 설정
    idempotency_ttl_sec: int = 86400
    idempotency_db_path: str = "/data/idem.db"
    
    # Outbox 설정
    outbox_db_path: str = "/data/outbox.db"
    outbox_max_retries: int = 10
    outbox_retry_interval_sec: float = 5.0
    
    # MQTT 공통 설정
    reconnect_max_backoff_sec: int = 120
    keepalive_sec: int = 30
    clean_session: bool = False
    
    # 재시도 설정
    max_retries: int = 5
    initial_delay: float = 1.0
    max_delay: float = 120.0
    backoff_factor: float = 2.0
    jitter: bool = True
    
    # 백프레셔 설정
    queue_maxsize: int = 1000
    drop_on_full: bool = False


class Settings(BaseModel):
    remote_mqtt: RemoteMqtt
    local_mqtt: LocalMqtt
    homeassistant_api: HomeAssistantAPI
    ha: HAConfig = HAConfig()
    geopolicy: GeoPolicy = GeoPolicy()
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
        
        # Home Assistant 환경에서 Local MQTT 자격 증명 자동 감지
        if data.get("local_mqtt", {}).get("enabled", True):
            local_mqtt = data.get("local_mqtt", {})
            
            # Home Assistant Add-on 환경에서 자동 MQTT 인증 정보 감지
            if not local_mqtt.get("username"):
                # Home Assistant Add-on 기본 MQTT 사용자명
                addon_username = os.getenv("MQTT_USERNAME", "addons")
                if addon_username:
                    local_mqtt["username"] = addon_username
                    log.info(f"Local MQTT 사용자명이 자동으로 설정되었습니다: {addon_username}")
            
            if not local_mqtt.get("password"):
                # Home Assistant Add-on 기본 MQTT 비밀번호
                addon_password = os.getenv("MQTT_PASSWORD")
                if addon_password:
                    local_mqtt["password"] = addon_password
                    log.info("Local MQTT 비밀번호가 자동으로 설정되었습니다")
                else:
                    log.warning("MQTT_PASSWORD 환경변수가 없습니다. Local MQTT 연결이 실패할 수 있습니다.")
            
            # Home Assistant 환경에서는 core-mosquitto 호스트 사용
            if local_mqtt.get("host") in ["localhost", "127.0.0.1"]:
                local_mqtt["host"] = "core-mosquitto"
                log.info("Local MQTT 호스트가 core-mosquitto로 자동 설정되었습니다")
            
            data["local_mqtt"] = local_mqtt
        
        return Settings(**data)

