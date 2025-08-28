#!/usr/bin/env bash
set -euo pipefail

# 환경변수 설정
export PYTHONPATH=/opt/app
export PYTHONUNBUFFERED=1

# Supervisor가 주입하는 토큰(있으면)과 옵션 파일 위치
# /data/options.json은 애드온 옵션이 저장되는 표준 경로입니다.
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-}"
export HA_OPTIONS_PATH="/data/options.json"

# 로그 레벨(기본값)
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo "Starting DX-Safety CAP Ingestor..."
echo "Python path: $PYTHONPATH"
echo "Log level: $LOG_LEVEL"
# 진짜 쓰는 파이썬 확인
/opt/venv/bin/python --version || true
command -v /opt/venv/bin/python || true

# 애플리케이션 실행 (PID 1로 교체)
exec /opt/venv/bin/python -m app.main
