#!/usr/bin/with-contenv bashio
set -e

# ---------- Remote MQTT ----------
REMOTE_HOST=$(bashio::config 'remote_mqtt.host')
REMOTE_PORT=$(bashio::config 'remote_mqtt.port')
REMOTE_TOPIC=$(bashio::config 'remote_mqtt.topic')
REMOTE_QOS=$(bashio::config 'remote_mqtt.qos')
REMOTE_SEC=$(bashio::config 'remote_mqtt.security_mode')
REMOTE_USER=$(bashio::config 'remote_mqtt.username')
REMOTE_PASS=$(bashio::config 'remote_mqtt.password')
REMOTE_KEEPALIVE=$(bashio::config 'remote_mqtt.keepalive')
REMOTE_CLEAN=$(bashio::config 'remote_mqtt.clean_session')
REMOTE_CLIENT_ID=$(bashio::config 'remote_mqtt.client_id')
REMOTE_CA=$(bashio::config 'remote_mqtt.ca_cert_path')
REMOTE_CRT=$(bashio::config 'remote_mqtt.client_cert_path')
REMOTE_KEY=$(bashio::config 'remote_mqtt.client_key_path')

export REMOTE_MQTT_HOST="${REMOTE_HOST}"
export REMOTE_MQTT_PORT="${REMOTE_PORT}"
export REMOTE_MQTT_USERNAME="${REMOTE_USER}"
export REMOTE_MQTT_PASSWORD="${REMOTE_PASS}"
export REMOTE_MQTT_CLIENT_ID="${REMOTE_CLIENT_ID}"
export REMOTE_MQTT_KEEPALIVE="${REMOTE_KEEPALIVE}"
export REMOTE_MQTT_CLEAN_SESSION="${REMOTE_CLEAN}"
# TLS/MTLS 플래그 (파이썬 쪽에서 처리)
if [ "${REMOTE_SEC}" = "tls" ] || [ "${REMOTE_SEC}" = "mtls" ]; then
  export REMOTE_MQTT_TLS=true
  export REMOTE_MQTT_CA_CERT="${REMOTE_CA}"
  export REMOTE_MQTT_CLIENT_CERT="${REMOTE_CRT}"
  export REMOTE_MQTT_CLIENT_KEY="${REMOTE_KEY}"
else
  export REMOTE_MQTT_TLS=false
fi
export REMOTE_TOPIC="${REMOTE_TOPIC}"

# ---------- Local MQTT ----------
LOCAL_HOST=$(bashio::config 'local_mqtt.host')
LOCAL_PORT=$(bashio::config 'local_mqtt.port')
LOCAL_PREFIX=$(bashio::config 'local_mqtt.topic_prefix')
LOCAL_QOS=$(bashio::config 'local_mqtt.qos')
LOCAL_RETAIN=$(bashio::config 'local_mqtt.retain')
LOCAL_USER=$(bashio::config 'local_mqtt.username')
LOCAL_PASS=$(bashio::config 'local_mqtt.password')

# localhost면 core-mosquitto로 자동 치환
if [ "${LOCAL_HOST}" = "localhost" ]; then
  LOCAL_HOST="core-mosquitto"
fi

export LOCAL_MQTT_HOST="${LOCAL_HOST}"
export LOCAL_MQTT_PORT="${LOCAL_PORT}"
export LOCAL_MQTT_USERNAME="${LOCAL_USER}"
export LOCAL_MQTT_PASSWORD="${LOCAL_PASS}"
export LOCAL_TOPIC_PREFIX="${LOCAL_PREFIX}"
export LOCAL_MQTT_QOS="${LOCAL_QOS}"
export LOCAL_MQTT_RETAIN="${LOCAL_RETAIN}"

# ---------- HA API ----------
HA_URL=$(bashio::config 'homeassistant_api.url')
HA_TOKEN_OPT=$(bashio::config 'homeassistant_api.token')
# Supervisor가 제공하는 토큰 우선
if [ -n "${SUPERVISOR_TOKEN:-}" ]; then
  export HA_TOKEN="${SUPERVISOR_TOKEN}"
else
  export HA_TOKEN="${HA_TOKEN_OPT}"
fi
export HA_BASE_URL="${HA_URL}"

# ---------- Policy ----------
SEV=$(bashio::config 'policy.severity_threshold')
DIST=$(bashio::config 'policy.radius_km_buffer')
export SEVERITY_THRESHOLD="${SEV}"
export DISTANCE_KM_THRESHOLD="${DIST}"     # Phase5 정책: radius_km_buffer를 distance 기준으로 사용
# geo 결합 모드는 운영 편의상 AND 기본 (필요시 config.yaml에 geopolicy_mode 추가)
export GEO_MODE="AND"

# ---------- Observability ----------
METRICS_PORT=$(bashio::config 'observability.http_port')
METRICS_ENABLED=$(bashio::config 'observability.metrics_enabled')
export METRICS_PORT="${METRICS_PORT}"
export METRICS_ENABLED="${METRICS_ENABLED}"

# ---------- Reliability ----------
export IDEMPOTENCY_TTL_SEC="$(bashio::config 'reliability.idempotency_ttl_sec')"
export PUBLISH_MAX_RETRIES="$(bashio::config 'reliability.max_retries')"
export BACKOFF_INITIAL_SEC="$(bashio::config 'reliability.initial_delay')"
export BACKOFF_MAX_SEC="$(bashio::config 'reliability.max_delay')"

# 운영 플래그
export DRY_RUN="false"
export ROLLBACK_MODE="false"
export PYTHONPATH="/opt/app"

# ---------- 실행 ----------
exec python3 -m main
