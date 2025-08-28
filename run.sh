#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=/opt/app
export PYTHONUNBUFFERED=1
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# 옵션 안전 복사 (권한 644로)
if [ -r /data/options.json ]; then
  mkdir -p /run
  cp /data/options.json /run/options.json
  chmod 644 /run/options.json
  export HA_OPTIONS_PATH="/run/options.json"
else
  # fallback: 그대로 /data 사용 (권한이 이미 열렸다면)
  export HA_OPTIONS_PATH="/data/options.json"
fi

echo "Starting DX-Safety CAP Ingestor..."
echo "Python path: $PYTHONPATH"
echo "Log level: $LOG_LEVEL"
/opt/venv/bin/python --version || true
command -v /opt/venv/bin/python || true

# PID 1 교체
exec /opt/venv/bin/python -m app.main
