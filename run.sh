#!/usr/bin/env bash
set -euo pipefail

# 환경변수 설정
export PYTHONPATH=/opt/app
export PYTHONUNBUFFERED=1

# 로그 레벨 설정 (기본값)
export LOG_LEVEL=${LOG_LEVEL:-INFO}

echo "Starting DX-Safety CAP Ingestor..."
echo "Python path: $PYTHONPATH"
echo "Log level: $LOG_LEVEL"

python3 -m app.main